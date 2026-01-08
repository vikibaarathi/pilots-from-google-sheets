import json
import logging
import gspread
import os
from RHUI import UIField, UIFieldType

DEBUG = False


class Gpilot():

    CONST_CREDENTIALS = 'credentials.json'

    def __init__(self,rhapi):
        self.logger = logging.getLogger(__name__)
        self._rhapi = rhapi
        
    def init_plugin(self,args):      
        self.logger.info("Starting Google Pilot plugin")
        self.init_ui(args)

    def init_ui(self,args):
        ui = self._rhapi.ui
        ui.register_panel("gpilot-import", "Pilots from Google Sheets Import", "format")
        ui.register_quickbutton("gpilot-import", "gpilot-import-button", "Import", self.import_pilot)
        ui.register_quickbutton("gpilot-import", "gpilot-update-button", "Update Pilot Details", self.update_pilot_details)
        gpilot_form_name = UIField(name = 'gpilot-form-name', label = 'Google Sheet Name', field_type = UIFieldType.TEXT, desc = "The name of the Google Sheet. With spaces and all. Please make sure there is at least 1 col called Name and 1 called Callsign on the first sheet.")
        fields = self._rhapi.fields
        fields.register_option(gpilot_form_name, "gpilot-import")

    def import_pilot(self, args):
        self._rhapi.ui.message_notify("Beginning Google Sheets Import....")
        credentials = self.get_credentials()
        filename = self._rhapi.db.option("gpilot-form-name")
        filenamenotempty = True if filename else False
        if credentials is not None and filenamenotempty:
            gc = gspread.service_account_from_dict(credentials)
            try:
                
                sh = gc.open(filename)
                all_records = sh.sheet1.get_all_records()
                self.save_pilot(all_records)
            except Exception as x:
                print(x)
                self._rhapi.ui.message_notify("Google Sheet Import Error - See log")
                self.logger.warning("Google Sheet not found" + str(x))

    def update_pilot_details(self, args):
        self._rhapi.ui.message_notify("Beginning Pilot Details Update....")
        credentials = self.get_credentials()
        filename = self._rhapi.db.option("gpilot-form-name")
        filenamenotempty = True if filename else False
        if credentials is not None and filenamenotempty:
            gc = gspread.service_account_from_dict(credentials)
            try:
                sh = gc.open(filename)
                all_records = sh.sheet1.get_all_records()
                self.update_pilots_from_sheet(all_records)
            except Exception as x:
                print(x)
                self._rhapi.ui.message_notify("Google Sheet Update Error - See log")
                self.logger.warning("Google Sheet Update Error: " + str(x))

    def get_credentials(self):
        here = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(here, self.CONST_CREDENTIALS)
        
        try:
            f = open(filename)
            data = json.load(f)
            f.close()
            return data
        except:
            self.logger.warning("Credentials file not found")
            self._rhapi.ui.message_notify("Credentials file not found. Please refer documentation.")
            data = None
            return data

    def save_pilot(self, all_records):
        
        for idx, record in enumerate(all_records):
            pilotnumber = str(idx + 1)
            pilotname = record["Name"] if (record["Name"] and record["Name"] is not None) else "~Pilot "+ pilotnumber + " Name"
            pilotcallsign = record["Callsign"] if (record["Callsign"] and record["Callsign"] is not None) else "~Callsign "+ pilotnumber
            pilot = {
                "name": pilotname,
                "callsign": pilotcallsign
            }
            if "Phonetic" in record:
                pilotphonetic = record["Phonetic"] if (record["Phonetic"] and record["Phonetic"] is not None) else ""
                pilot["phonetic"] = pilotphonetic
            if "Colour" in record:
                pilotcolor = record["Colour"] if (record["Colour"] and record["Colour"] is not None) else "#ff0055"
                pilot["color"] = pilotcolor
            if "MGP ID" in record:
                pilotmgpid = record["MGP ID"] if (record["MGP ID"] and record["MGP ID"] is not None) else ""
            if "FPVS UUID" in record:
                pilottracksideid = record["FPVS UUID"] if (record["FPVS UUID"] and record["FPVS UUID"] is not None) else ""
            if "Country" in record:
                pilotcountry = record["Country"] if (record["Country"] and record["Country"] is not None) else " "
            if "ELRS Bind Phrase" in record:
                pilot_elrs = record["ELRS Bind Phrase"] if (record["ELRS Bind Phrase"] and record["ELRS Bind Phrase"] is not None) else " "
            if "Velocidrone UUID" in record:
                pilot_velo_uuid = record["Velocidrone UUID"] if (record["Velocidrone UUID"] and record["Velocidrone UUID"] is not None) else " "
                pilotcountry = record["Country"] if (record["Country"] and record["Country"] is not None) else ""
            if "FAI Number" in record:
                pilotfainumber = record["FAI Number"] if (record["FAI Number"] and record["FAI Number"] is not None) else ""

            existingpilot = self.check_existing_pilot(pilot)
            if not existingpilot:
                self._rhapi.db.pilot_add(name=pilot["name"],
                                         callsign=pilot["callsign"],
                                         phonetic=pilot["phonetic"],
                                         color=pilot["color"])
                self.logger.info("Added pilot " + pilot["name"] + "-" + pilot["callsign"] + " with id:"
                                 + str(self._rhapi.db.pilots[-1].id))
                current_id = self._rhapi.db.pilots[-1].id

                contains_mgp_id = False
                contains_fpvs_uuid = False
                contains_country = False
                contains_elrs = False
                contains_velo_uid = False
                if DEBUG:
                    self.logger.info(f"attribute are : ")
                contains_fainumber = False
                for i in range(len(self._rhapi.fields.pilot_attributes)):
                    if DEBUG:
                        self.logger.info(self._rhapi.fields.pilot_attributes[i].name)
                    if self._rhapi.fields.pilot_attributes[i].name == 'mgp_pilot_id':
                        contains_mgp_id = True
                    if self._rhapi.fields.pilot_attributes[i].name == 'fpvs_uuid':
                        contains_fpvs_uuid = True
                    if self._rhapi.fields.pilot_attributes[i].name == 'country':
                        contains_country = True
                    if self._rhapi.fields.pilot_attributes[i].name == 'comm_elrs':
                        contains_elrs = True
                    if self._rhapi.fields.pilot_attributes[i].name == 'velo_uid':
                        contains_velo_uid = True

                    if self._rhapi.fields.pilot_attributes[i].name == 'fainumber':
                        contains_fainumber = True
                pilot_attributes = {}
                if contains_mgp_id and "MGP ID" in record:
                    pilot_attributes["mgp_pilot_id"] = pilotmgpid
                if contains_fpvs_uuid and "FPVS UUID" in record:
                    pilot_attributes["fpvs_uuid"] = pilottracksideid
                if contains_country and "Country" in record:
                    pilot_attributes["country"] = pilotcountry
                if contains_elrs and "ELRS Bind Phrase" in record:
                    pilot_attributes['comm_elrs'] = pilot_elrs
                if contains_velo_uid and "Velocidrone UUID" in record:
                    pilot_attributes["velo_uid"] = pilot_velo_uuid
                if contains_fainumber and "FAI Number" in record:
                    pilot_attributes["fainumber"] = pilotfainumber
                self._rhapi.db.pilot_alter(current_id, attributes=pilot_attributes)
        self._rhapi.ui.message_notify("Import complete, please refresh.")
        self._rhapi.ui.broadcast_pilots()

    def update_pilots_from_sheet(self, all_records):
        localpilots = self._rhapi.db.pilots
        updated_count = 0
        
        # Check which custom attributes exist
        contains_country = False
        contains_elrs = False
        contains_elrs_active = False
        contains_velo_uid = False
        
        for i in range(len(self._rhapi.fields.pilot_attributes)):
            if self._rhapi.fields.pilot_attributes[i].name == 'country':
                contains_country = True
            if self._rhapi.fields.pilot_attributes[i].name == 'comm_elrs':
                contains_elrs = True
            if self._rhapi.fields.pilot_attributes[i].name == 'elrs_active':
                contains_elrs_active = True
            if self._rhapi.fields.pilot_attributes[i].name == 'velo_uid':
                contains_velo_uid = True
        
        # Loop through all pilots in database
        for pilot in localpilots:
            # Find matching record in Google Sheet by name
            matching_record = None
            for record in all_records:
                record_name = record.get("Name", "")
                if record_name and record_name == pilot.name:
                    matching_record = record
                    break
            
            if matching_record:
                # Prepare update data
                update_params = {}
                pilot_attributes = {}
                
                # Update callsign if present
                if "Callsign" in matching_record and matching_record["Callsign"]:
                    update_params["callsign"] = matching_record["Callsign"]
                
                # Update phonetic if present
                if "Phonetic" in matching_record and matching_record["Phonetic"] is not None:
                    update_params["phonetic"] = matching_record["Phonetic"]
                
                # Update color if present
                if "Colour" in matching_record and matching_record["Colour"]:
                    update_params["color"] = matching_record["Colour"]
                
                # Update country attribute if present and field exists
                if contains_country and "Country" in matching_record and matching_record["Country"] is not None:
                    pilot_attributes["country"] = matching_record["Country"]
                
                # Update ELRS Bind Phrase attribute if present and field exists
                if contains_elrs and "ELRS Bind Phrase" in matching_record and matching_record["ELRS Bind Phrase"] is not None:
                    pilot_attributes["comm_elrs"] = matching_record["ELRS Bind Phrase"]
                    # Also toggle elrs_active to true if the field exists
                    if contains_elrs_active:
                        pilot_attributes["elrs_active"] = True
                
                # Update Velocidrone UUID attribute if present and field exists
                if contains_velo_uid and "Velocidrone UUID" in matching_record and matching_record["Velocidrone UUID"] is not None:
                    pilot_attributes["velo_uid"] = matching_record["Velocidrone UUID"]
                
                # Perform update if there are any changes
                if update_params or pilot_attributes:
                    self._rhapi.db.pilot_alter(pilot.id, **update_params, attributes=pilot_attributes)
                    updated_count += 1
                    self.logger.info("Updated pilot " + pilot.name + " (ID: " + str(pilot.id) + ")")
        
        self._rhapi.ui.message_notify("Update complete. Updated " + str(updated_count) + " pilot(s).")
        self._rhapi.ui.broadcast_pilots()

    def check_existing_pilot(self,pilot):
        localpilots = self._rhapi.db.pilots
        existing = False
        for localpilot in localpilots:
            if (localpilot.name == pilot["name"] or localpilot.callsign == pilot["callsign"]):
                existing = True

        return existing
        
