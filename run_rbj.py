# -*- coding: utf-8 -*-
#¸¸.·´¯`·.¸¸.·´¯`·.¸¸
# ║╚╔═╗╝║  │┌┘─└┐│  ▄█▀‾
# ==================== #
#  Run RBJ Checks v1.1 #
# Nat Cagle 2022-08-03 #
# ==================== #

# ArcPy aliasing
import arcpy as ap
from arcpy import AddMessage as write
# STOP! Hammer time
from datetime import datetime as dt
# System Modules
import os
import sys
import shutil



#            __________________________________
#           | Runs RBJ checks on a geodatabase |
#           | using an RBJ file, RBJ Reviewer  |
#           | Database, and an optional AOI    |
#           | polygon. Outputs a Frequency     |
#           | Report Excel document and fully  |
#           | attributed RBJ error shapefiles. |
#           |                                  |
#           |  *quack*                         |
#           |                       *quack*    |
#           |            *quack*               |
#           |                                  |
#      _    /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
#   __(.)< ‾
#~~~\___)~~~



'''
╔═════════════════╗
║ Notes and To-Do ║
╚═════════════════╝

## 2 hashtags in the code - recent changes/updates
### 3 hashtags in the code - unique variable or identifier
#### 4 hashtags in the code - things to be updated

## Recent Changes
  - Something that has recently been updated. A dynamic list that is preserved/reset
	in each new version

#### Update Plans
  - Option to provide name that is prepended to output files.
  - change output frequency report name from "RBJ_error_frequency_report" to "RBJ_frequency_report"
  - zip the output shapefiles for easy transfer

'''



'''
╔═══════════════════╗
║ General Functions ║
╚═══════════════════╝
'''
#-----------------------------------
def runtime(start, finish): # Time a process or code block
	# Add a start and finish variable markers surrounding the code to be timed
	#from datetime import datetime as dt
	#start/finish = dt.now()
	# Returns string of formatted elapsed time between start and finish markers
	time_delta = (finish - start).total_seconds()
	h = int(time_delta/(60*60))
	m = int((time_delta%(60*60))/60)
	s = time_delta%60.
	#time_elapsed = "{}:{:>02}:{:>05.4f}".format(h, m, s) # 00:00:00.0000
	if h == 1:
		hour_grammar = "hour"
	else:
		hour_grammar = "hours"
	if m == 1:
		minute_grammar = "minute"
	else:
		minute_grammar = "minutes"
	if h and m and s:
			time_elapsed = "{} {} {} {} and {} seconds".format(h, hour_grammar, m, minute_grammar, round(s))
	elif not h and m and s:
		time_elapsed = "{} {} and {:.1f} seconds".format(m, minute_grammar, s)
	elif not h and not m and s:
		time_elapsed = "{:.3f} seconds".format(s)
	else:
		time_elapsed = 0
	return time_elapsed

def get_count(fc): # Returns feature count
    results = int(ap.GetCount_management(fc).getOutput(0))
    return results

def check_data_reviewer(in_out): # If any of the tools that require the Data Reviewer license are selected, check out the Data Reviewer license
	class LicenseError(Exception):
		pass
	try:
		if ap.CheckExtension('datareviewer') == 'Available' and in_out == 'out':
			write("\n~~ Checking out Data Reviwer Extension ~~\n")
			ap.CheckOutExtension('datareviewer')
		elif in_out == 'in':
			write("\n~~ Checking Data Reviwer Extension back in ~~\n")
			ap.CheckInExtension('datareviewer')
		else:
			raise LicenseError
	except LicenseError:
		ap.AddError("Data Reviwer license is unavailable")

def export_dr_to_shp(reviewer_workspace, fields, output_path):
	# Importing license level
	try:
		import arcinfo
	except:
		arcpy.AddError("This tool requires an ArcInfo license.")
		sys.exit("ArcInfo license not available")

	session = 'Session 1'
	field_list = fields.split(";")

	# Check if shapefiles created by script exists. If so error and do not process.
	ShapeName = 'RBJ_error.shp'
	FileName = ShapeName[:-4] + "_Table.dbf"
	FinalPointShape = output_path + "\\" + ShapeName[:-4] + '_pnt.shp'
	FinalLineShape = output_path + "\\" + ShapeName[:-4] + '_crv.shp'
	FinalPolygonShape = output_path + "\\" + ShapeName[:-4] + '_srf.shp'
	Table = output_path + "\\" + FileName

	# Create a temporary database for processing errors
	TempWksp = "in_memory"
	arcpy.AddMessage("Temporary in_memory workspace created")

	LineShape = TempWksp + "\\RevLine"
	PolyShape = TempWksp + "\\RevPoly"
	LineShapeSingle = TempWksp + "\\RevLine_single"
	LineShapeDissolve = TempWksp + "\\RevLine_dissolve"
	PolyShapeSingle = TempWksp + "\\RevPoly_single"
	PolyShapeDissolve = TempWksp + "\\RevPoly_dissolve"
	temp_fc_pnt = TempWksp + "\\TempPoint"
	temp_fc_crv = TempWksp + "\\TempLine"
	temp_fc_srf = TempWksp + "\\TempPoly"

	# Paths to tables in Reviewer workspace
	SessionsTable = reviewer_workspace + "\\REVSESSIONTABLE"
	REVTABLEMAIN = reviewer_workspace + "\\REVTABLEMAIN"
	REVTABLEPOINT = reviewer_workspace + "\\REVDATASET\\REVTABLEPOINT"
	REVTABLELINE = reviewer_workspace + "\\REVDATASET\\REVTABLELINE"
	REVTABLEPOLY = reviewer_workspace + "\\REVDATASET\\REVTABLEPOLY"

	# Check to see if output shapefile already exists. If exists do not process.
	Exists = False
	if arcpy.Exists(FinalPointShape):
		arcpy.AddError("Point shapefile already exists in output workspace " + FinalPointShape)
		Exists = True
	if arcpy.Exists(FinalLineShape):
		arcpy.AddError("Point shapefile already exists in output workspace " + FinalLineShape)
		Exists = True
	if arcpy.Exists(FinalPolygonShape):
		arcpy.AddError("Point shapefile already exists in output workspace " + FinalPolygonShape)
		Exists = True
	if arcpy.Exists(Table):
		arcpy.AddError("Table for non geometry errors already exists in output workspace " + Table)
		Exists = True

	if not Exists:
		# Local variables:
		TableFields = fields

		RenameFields = ["ORIGINTABLE", "ORIGINCHECK", "REVIEWSTATUS", "CORRECTIONSTATUS", "VERIFICATIONSTATUS", "REVIEWTECHNICIAN", "REVIEWDATE", "CORRECTIONTECHNICIAN", "CORRECTIONDATE", "VERIFICATIONTECHNICIAN", "VERIFICATIONDATE", "LIFECYCLESTATUS", "LIFECYCLEPHASE"]

		NewNames = ["ORIG_TABLE", "ORIG_CHECK", "ERROR_DESC", "COR_STATUS", "VER_STATUS", "REV_TECH", "REV_DATE", "COR_TECH", "COR_DATE", "VER_TECH", "VER_DATE", "STATUS", "PHASE"]

		PointFieldInfo = "REVTABLEPOINT.SHAPE SHAPE VISIBLE NONE; " + "REVTABLEPOINT.OID REVTABLEPOINT.OID HIDDEN NONE; " + "REVTABLEPOINT.LINKGUID REVTABLEPOINT.LINKGUID HIDDEN NONE; " + "REVTABLEPOINT.SESSIONID SESSIONID HIDDEN NONE; "
		LineFieldInfo = "REVTABLELINE.SHAPE SHAPE VISIBLE NONE; " + "REVTABLELINE.OID REVTABLELINE.OID HIDDEN NONE; " + "REVTABLELINE.LINKGUID REVTABLELINE.LINKGUID HIDDEN NONE; " + "REVTABLELINE.SESSIONID SESSIONID HIDDEN NONE; "
		PolyFieldInfo = "REVTABLEPOly.SHAPE SHAPE VISIBLE NONE; " + "REVTABLEPOly.OID REVTABLEPOly.OID HIDDEN NONE; " + "REVTABLEPOly.LINKGUID REVTABLEPOly.LINKGUID HIDDEN NONE; " + "REVTABLEPOly.SESSIONID SESSIONID HIDDEN NONE; "
		TableFieldInfo = "; "

		try:
			sessionIDs = []
			WhereClause = ""
			TotalErrors = 0

			# -------------------------------------------------------
			# Determine what fields will be in output shapefile\table
			# -------------------------------------------------------

			# Get RevTableMain and RevTablePoint fully qualified names
			arcpy.env.workspace = reviewer_workspace
			RevMainFullName = "REVTABLEMAIN."
			RevPointFullName = "REVTABLEPOINT."
			RevLineFullName = "REVTABLELINE."
			RevPolyFullName = "REVTABLEPOLY."

			PointFieldInfo = "SHAPE SHAPE VISIBLE NONE; " + RevPointFullName + "OBJECTID OID HIDDEN NONE; TempPoint.LINKGUID TempPoint.LINKGUID HIDDEN " + "NONE; TempPoint.SESSIONID TempPoint.SESSIONID HIDDEN NONE; "
			LineFieldInfo = "SHAPE SHAPE VISIBLE NONE; " + RevLineFullName + "OBJECTID OID HIDDEN NONE; TempLine.LINKGUID TempLine.LINKGUID HIDDEN " + "NONE; TempLine.SESSIONID TempLine.SESSIONID HIDDEN NONE; "
			PolyFieldInfo = "SHAPE SHAPE VISIBLE NONE; " + RevPolyFullName + "OBJECTID OID HIDDEN NONE; TempPoly.LINKGUID TempPoly.LINKGUID HIDDEN " + "NONE; TempPoly.SESSIONID TempPoly.SESSIONID HIDDEN NONE; "
			TableFieldInfo = "; "

			# Get the fields in RevTableMain
			for field in arcpy.Describe(REVTABLEMAIN).fields:
				name = field.name

				# For each field determine if it will be visible in output based on
				# fields input value
				view = "HIDDEN"
				if name in field_list:
					view = "VISIBLE"

				# If the field is over 10 characters (in RenameFields array) replace with new name (from NewNames array).
				outname = name
				if name in RenameFields:
					i = RenameFields.index(name)
					outname = NewNames[i]

				# Update the information of the shapefile and table outputs
				PointFieldInfo = PointFieldInfo + RevMainFullName + name + " " + outname + " " + view + " NONE; "
				LineFieldInfo = LineFieldInfo + RevMainFullName + name + " " + outname + " " + view + " NONE; "
				PolyFieldInfo = PolyFieldInfo + RevMainFullName + name + " " + outname + " " + view + " NONE; "
				TableFieldInfo = TableFieldInfo + name + " " + outname + " " + view + " NONE; "

			PointFieldInfo = PointFieldInfo[:-2]
			LineFieldInfo = LineFieldInfo[:-2]
			PolyFieldInfo = PolyFieldInfo[:-2]
			TableFieldInfo = TableFieldInfo[:-2]

			# ---------------------------------------------------------
			# Build the whereclause to select the input session records
			# ---------------------------------------------------------

			# Get the Session ID(s)
			RowCount = get_count(SessionsTable)
			with ap.da.SearchCursor(SessionsTable, ["SESSIONNAME"]) as scursor:
				for srow in scursor:
					if srow[0] in session:
						sessionIDs.append(str(srow[0]))

			# If you did not select all the session, make a whereclause to select only features from the desired sessions
			if len(sessionIDs) != RowCount:
				SessionFieldName = arcpy.AddFieldDelimiters(reviewer_workspace, "SessionID")
				WhereClause = "({0} = {1})".format(SessionFieldName, sessionIDs[0])

			# Expression parameter of make layer and create table view only allows 247 characters.
			# If the number of sessions selected is more than 13 this limit will be reached.
			if len(WhereClause) > 222:
				# Return error and do not process records
				arcpy.AddMessage(WhereClause)
				arcpy.AddMessage("Whereclause length {0}".format(len(WhereClause)))
				arcpy.AddError("Too many sessions were selected. The whereclause for selecting only records from the chosen session will be too long. You must select less than 12 sessions or you must select all.")

			else:
				# ----------------------
				# Add XY to Point Errors
				# ----------------------

				# Make a point layer and join to RevTableMain to get error information
				arcpy.AddMessage("\nProcessing Point Errors...")
				arcpy.MakeFeatureLayer_management(REVTABLEPOINT, "TempPoint", WhereClause, "", "")

				count = 0
				count = get_count("TempPoint")
				if count >= 1:
					TotalErrors = TotalErrors + count
					arcpy.AddMessage("  .. {0} point features will be processed.".format(count))
					arcpy.AddMessage("  .. Converting reviewer point geometries.")

					arcpy.FeatureClassToFeatureClass_conversion("TempPoint", TempWksp, "TempPoint")

					arcpy.MakeFeatureLayer_management(temp_fc_pnt, "Final_pnt", "", "", "")
					arcpy.AddMessage("\nJoining points to RevTableMain for error information.")
					arcpy.AddJoin_management("Final_pnt", "LINKGUID", REVTABLEMAIN, "ID", "KEEP_COMMON")

					# Make new layer with appropriate output field names
					shape_pnt = ShapeName[:-4] + '_pnt'
					arcpy.MakeFeatureLayer_management("Final_pnt", shape_pnt, "", "", PointFieldInfo)

					# Save the layers as a shapefile
					arcpy.AddMessage("Creating shapefiles.")
					arcpy.FeatureClassToShapefile_conversion(shape_pnt, output_path)

				else:
					arcpy.AddMessage("  .. No point errors exist in selected session.")

				# -------------------------------
				# Add Line Errors to XY Shapefile
				# -------------------------------

				# Make Line Layer with only records from selected sessions
				arcpy.AddMessage("\nProcessing Line Errors...")
				arcpy.MakeFeatureLayer_management(REVTABLELINE, "TempLine", WhereClause, "", "")

				count = 0
				count = get_count("TempLine")
				if count >= 1:
					TotalErrors = TotalErrors + count
					arcpy.AddMessage("  .. {0} line features will be processed.".format(count))
					arcpy.AddMessage("  .. Converting reviewer line geometries.")

					# Explode into single part features
					arcpy.MultipartToSinglepart_management("TempLine", LineShapeSingle)
					# Run repair geometry incase any bad geometry created.
					arcpy.RepairGeometry_management(LineShapeSingle)
					# Dissolve the points into a multi-part point using the LinkGUID field
					arcpy.Dissolve_management(LineShapeSingle, LineShapeDissolve, "LINKGUID", "", "MULTI_PART", "DISSOLVE_LINES")

					arcpy.FeatureClassToFeatureClass_conversion(LineShapeDissolve, TempWksp, "TempLine")

					arcpy.MakeFeatureLayer_management(temp_fc_crv, "Final_crv", "", "", "")
					arcpy.AddMessage("Joining lines to RevTableMain for error information.")
					arcpy.AddJoin_management("Final_crv", "LINKGUID", REVTABLEMAIN, "ID", "KEEP_COMMON")

					# Make new layer with appropriate output field names
					shape_crv = ShapeName[:-4] + '_crv'
					arcpy.MakeFeatureLayer_management("Final_crv", shape_crv, "", "", LineFieldInfo)

					# Save the layers as a shapefile
					arcpy.AddMessage("Creating shapefiles.")
					arcpy.FeatureClassToShapefile_conversion(shape_crv, output_path)

				else:
					arcpy.AddMessage("  .. No line errors exist in selected session.")

				# ----------------------------------
				# Add Polygon Errors to XY Shapefile
				# ----------------------------------

				# Make Polygon Layer with only records from selected sessions
				arcpy.AddMessage("\nProcessing Polygon Errors...")
				arcpy.MakeFeatureLayer_management(REVTABLEPOLY, "TempPoly", WhereClause, "", PolyFieldInfo)

				count = 0
				count = get_count("TempPoly")
				if count >= 1:
					TotalErrors = TotalErrors + count
					arcpy.AddMessage("  .. {0} polygon features will be exported to shapefile.".format(count))
					arcpy.AddMessage("  .. Converting reviewer polygon geometries.")

					# Explode into single part features
					arcpy.MultipartToSinglepart_management("TempPoly", PolyShapeSingle)
					# Run repair geometry incase any bad geometry created.
					arcpy.RepairGeometry_management(PolyShapeSingle)
					# Dissolve the points into a multi-part point using the LinkGUID field
					arcpy.Dissolve_management(PolyShapeSingle, PolyShapeDissolve, "LINKGUID", "", "MULTI_PART", "DISSOLVE_LINES")

					arcpy.FeatureClassToFeatureClass_conversion(PolyShapeDissolve, TempWksp, "TempPoly")

					arcpy.MakeFeatureLayer_management(temp_fc_srf, "Final_srf", "", "", "")
					arcpy.AddMessage("Joining polygons to RevTableMain for error information.")
					arcpy.AddJoin_management("Final_srf", "LINKGUID", REVTABLEMAIN, "ID", "KEEP_COMMON")

					# Make new layer with appropriate output field names
					shape_srf = ShapeName[:-4] + '_srf'
					arcpy.MakeFeatureLayer_management("Final_srf", shape_srf, "", "", PolyFieldInfo)

					# Save the layers as a shapefile
					arcpy.AddMessage("Creating shapefiles.")
					arcpy.FeatureClassToShapefile_conversion(shape_srf, output_path)

				else:
					arcpy.AddMessage("  .. No polygon errors exist in selected session.")

				# -------------------------------
				# Process Errors with no geometry
				# -------------------------------

				arcpy.AddMessage("\nProcessing errors with no geometry...")
				count = 0

				# To find only table records, add the GeometryType field records that are null to the list
				GeoFieldName = arcpy.AddFieldDelimiters(reviewer_workspace, "GEOMETRYTYPE")
				if len(sessionIDs) != RowCount:
					WhereClause = WhereClause + " AND " + GeoFieldName + " IS NULL"
				else:
					WhereClause = GeoFieldName + " IS NULL"

				# Create a table view of records that meet query
				arcpy.MakeTableView_management(REVTABLEMAIN, "RevTable", WhereClause, "#", TableFieldInfo)
				count = get_count("RevTable")

				# If errors with no geometry exist
				if count >= 1:
					TotalErrors = TotalErrors + count
					arcpy.AddMessage("  .. {0} errors exist with no geometry and will be exported to a table.".format(count))

					# Create the .dbf table of errors
					arcpy.TableToTable_conversion("RevTable", output_path, FileName)

				else:
					arcpy.AddMessage("No errors exist with no geometry in selected session.  No table will be created.")

				# Provide summary information about processing
				arcpy.AddMessage("\nTotal Errors Exported: " + str(TotalErrors))
				if arcpy.Exists(FinalPointShape):
					arcpy.AddMessage("Output point shapefile path " + FinalPointShape)
				if arcpy.Exists(FinalLineShape):
					arcpy.AddMessage("Output line shapefile path " + FinalLineShape)
				if arcpy.Exists(FinalPolygonShape):
					arcpy.AddMessage("Output polygon shapefile path " + FinalPolygonShape)
				if count >= 1:
					arcpy.AddMessage("Output Table path " + Table)

				if arcpy.Exists("RevTable"):
					arcpy.Delete_management("RevTable")

			del REVTABLEMAIN,  REVTABLEPOINT, REVTABLELINE, REVTABLEPOLY

		except SystemExit:
			# If the script fails...
			arcpy.AddMessage("Exiting the script")
			tb = sys.exc_info()[2]
			arcpy.AddMessage("Failed at step 3 \n" "Line %i" % tb.tb_lineno)
			arcpy.AddMessage(e.message)

			# Delete the output shapefile and table if created (likely created incorrectly)
			if arcpy.Exists(FinalPointShape):
				arcpy.Delete_management(FinalPointShape)
			if arcpy.Exists(FinalLineShape):
				arcpy.Delete_management(FinalLineShape)
			if arcpy.Exists(FinalPolygonShape):
				arcpy.Delete_management(FinalPolygonShape)
			if arcpy.Exists(Table):
				arcpy.Delete_management(Table)

		finally:
			# Delete temporary layers\shapefiles
			arcpy.AddMessage("Deleting temporary files.")
			if arcpy.Exists("RevLine"):
				arcpy.Delete_management("RevLine")
			if arcpy.Exists("RevPoly"):
				arcpy.Delete_management("RevPoly")
			if arcpy.Exists("Final_pnt"):
				arcpy.Delete_management("Final_pnt")
			if arcpy.Exists("TempPoint"):
				arcpy.Delete_management("TempPoint")
			if arcpy.Exists(LineShapeSingle):
				arcpy.Delete_management(LineShapeSingle)
			if arcpy.Exists(LineShapeDissolve):
				arcpy.Delete_management(LineShapeDissolve)
			if arcpy.Exists(PolyShapeSingle):
				arcpy.Delete_management(PolyShapeSingle)
			if arcpy.Exists(PolyShapeDissolve):
				arcpy.Delete_management(PolyShapeDissolve)
			if arcpy.Exists(temp_fc_pnt):
				arcpy.Delete_management(temp_fc_pnt)
			if arcpy.Exists(temp_fc_crv):
				arcpy.Delete_management(temp_fc_crv)
			if arcpy.Exists(temp_fc_srf):
				arcpy.Delete_management(temp_fc_srf)
			arcpy.RefreshCatalog(output_path)

	else:
		arcpy.AddError("Please choose new output directory or delete existing files")


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


'''
╔═══════════════╗
║ Main Function ║
╚═══════════════╝
'''

def main(*argv):
	### [0] Geodatabase for RBJ checks - Workspace
	production_gdb = argv[0]
	### [1] RBJ File - File
	rbj_file = argv[1]
	### [2] RBJ Reviewer Geodatabase - Workspace
	reviewer_gdb = argv[2]
	### [3] - Output Folder - Folder
	output_folder = argv[3]
	### [4] AOI polygon of review area - Feature Class - {Optional}
	AOI = argv[4]
	#write("AOI: {}".format(AOI))
	#write("Type: {}".format(type(AOI)))
	#if not AOI:
	#	AOI = ""
	# Reviewer Session - must exist before executing this script.
	session =  "Session 1 : Session 1"
	rbj_name = os.path.split(rbj_file)[-1]
	gdb_name = os.path.split(production_gdb)[-1]


	# Execute Reviewer Batch Job function
	rbj_start = dt.now()
	write("\nRunning '{0}' RBJ checks on\n'{1}'...".format(rbj_name, gdb_name))
	ap.ExecuteReviewerBatchJob_Reviewer(reviewer_gdb, session, rbj_file, production_gdb, AOI)
	rbj_finish = dt.now()
	write("Ran RBJ checks in {0}".format(runtime(rbj_start, rbj_finish)))

	# Create Frequency table of RBJ errors
	freq_start = dt.now()
	write("\nExporting Frequency Report as Excel file...")
	rev_table = reviewer_gdb + '\REVTABLEMAIN'
	freq_table = reviewer_gdb + '\REVTABLEMAIN_FREQUENCY'
	freq_fields = ["SUBTYPE", "CHECKTITLE", "ORIGINTABLE", "REVIEWSTATUS"]
	ap.Frequency_analysis(rev_table, freq_table, freq_fields)

	# Export the Frequency table as Excel doc to the output folder
	out_xls = output_folder + "\RBJ_error_frequency_report.xls"
	ap.TableToExcel_conversion(freq_table, out_xls)
	freq_finish = dt.now()
	write("Created Frequency Report in {0}".format(runtime(freq_start, freq_finish)))

	# Export RBJ errors to shapefiles in the output folder
	shp_start = dt.now()
	write("\nConverting Data Reviewer validation outputs to shapefiles...")
	rev_fields = 'RECORDID;OBJECTID;SUBTYPE;CHECKTITLE;ORIGINTABLE;ORIGINCHECK;REVIEWSTATUS;REVIEWTECHNICIAN;REVIEWDATE'
	export_dr_to_shp(reviewer_gdb, rev_fields, output_folder)
	shp_finish = dt.now()
	write("Exported error shapefiles in {0}".format(runtime(shp_start, shp_finish)))

	ap.AddWarning("\n\nFrequency Report is located here:\n{}\n".format(out_xls))
	ap.AddWarning("RBJ_error shapefiles are located here:\n{}\n".format(output_folder))


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


if __name__=='__main__':
	ap.env.overwriteOutput = True
	argv = tuple(ap.GetParameterAsText(i) for i in range(ap.GetArgumentCount()))
	check_data_reviewer('out')
	main(*argv)
	check_data_reviewer('in')
