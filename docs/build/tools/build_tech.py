from __future__ import annotations
import pathlib, yaml
C="C"; H,M,L="H","M","L"
TAX = {
  "surveillance-vehicle": ("Vehicle surveillance", {
    "alpr": ("Automated licence plate readers", [
      ("alpr-fixed","Fixed ALPR","Pole/structure-mounted, permanently sited at one location.",["license plate reader","fixed LPR","pole-mounted camera"],M),
      ("alpr-mobile","Mobile ALPR","Mounted on a patrol vehicle and reads while in motion.",["mobile LPR","vehicle-mounted plate reader"],M),
      ("alpr-covert","Covert ALPR","Concealed/disguised siting intended to avoid detection.",["covert LPR","concealed camera"],H),
      ("alpr-trailer","Trailer-mounted ALPR","Redeployable on a towed trailer, often solar-powered.",["LPR trailer","camera trailer plate reader"],M),
      ("alpr-checkpoint","Checkpoint ALPR","Deployed at a fixed screening chokepoint or border checkpoint.",["checkpoint LPR","border plate reader"],M),
    ]),
    "vehicle-fingerprint": ("Vehicle fingerprinting", [
      ("vehicle-fingerprint-reid","Vehicle fingerprint re-identification","Re-identifies a vehicle by make/model/colour/features without reading a plate.",["vehicle fingerprint","vehicle re-identification","make model color"],H),
    ]),
    "plate-data-commercial": ("Commercial plate-data purchase", [
      ("plate-data-commercial-purchase","Commercial plate-data purchase","Purchase of plate reads collected by a commercial (non-agency) network.",["commercial LPR data","plate data subscription","national plate database"],H),
    ]),
  }),
  "surveillance-video": ("Video surveillance", {
    "fixed-camera": ("Fixed and PTZ cameras", [
      ("camera-fixed-cctv","Fixed CCTV","Fixed field-of-view video camera.",["CCTV","fixed camera","surveillance camera"],L),
      ("camera-ptz","Pan-tilt-zoom camera","Operator-steerable pan/tilt/zoom camera.",["PTZ camera","pan tilt zoom"],M),
    ]),
    "private-camera-integration": ("Private-camera registry and integration", [
      ("private-camera-registry","Private-camera registry","A register of privately owned cameras with no live feed access.",["camera registry","register your camera"],M),
      ("private-camera-integration","Private-camera integration","Live private feeds integrated into an agency platform.",["camera integration","connect your camera"],H),
      ("private-camera-per-incident-request","Per-incident private-camera request","Consent-gated, per-incident footage requests from private owners.",["footage request","per-incident camera request"],M),
    ]),
    "video-analytics": ("Video analytics", [
      ("video-analytics-object","Object-detection analytics","Automated detection/classification of objects in a video stream.",["video analytics","object detection","person of interest search"],H),
      ("video-analytics-loitering","Behavioural video analytics","Flags loitering/anomalous movement in a video stream.",["loitering detection","anomaly video analytics"],H),
    ]),
    "camera-trailer": ("Camera trailers", [
      ("camera-trailer-video","Video camera trailer","Redeployable trailer carrying video (not primarily ALPR) cameras.",["camera trailer","mobile surveillance trailer"],M),
    ]),
  }),
  "body-worn-video": ("Body-worn and in-car video", {
    "body-worn-camera": ("Body-worn cameras", [
      ("bwc-recorded","Recorded body-worn camera","Records to storage for later review.",["body-worn camera","BWC","body cam"],M),
      ("bwc-livestream","Live-streaming body-worn camera","Streams live into an integration/RTCC platform.",["BWC livestream","live body camera","real-time streaming"],H),
    ]),
    "in-car-video": ("In-car video", [
      ("in-car-video-recorded","In-car video","Dash/in-car camera system.",["in-car video","dash cam","ICV"],L),
    ]),
  }),
  "biometric-id": ("Biometric identification", {
    "face-recognition": ("Face recognition", [
      ("face-verification-1to1","1:1 face verification","Confirms a claimed identity against one template.",["face verification","1:1 match"],C),
      ("face-identification-1ton","1:N face identification","Searches a face against a gallery of many.",["face recognition","1:N search","facial recognition"],C),
      ("face-retrospective","Retrospective face search","Searches recorded imagery after the fact.",["retrospective facial recognition","RFR"],C),
      ("face-live","Live face recognition","Matches faces against a watchlist in real time.",["live facial recognition","LFR","real-time face"],C),
      ("face-clustering","Face clustering","Groups unlabelled faces across media without a named gallery.",["face clustering","face grouping"],C),
    ]),
    "fingerprint": ("Fingerprint identification", [
      ("fingerprint-tenprint","Ten-print identification","Matches full ten-print sets (AFIS).",["AFIS","ten-print","fingerprint database"],C),
      ("fingerprint-latent","Latent print identification","Matches partial/latent prints from a scene.",["latent print","latent fingerprint"],C),
      ("fingerprint-mobile","Mobile fingerprint","Field mobile fingerprint capture/identification.",["mobile fingerprint","rapid ID"],C),
    ]),
    "iris": ("Iris recognition", [
      ("iris-recognition","Iris recognition","Identifies by iris pattern.",["iris recognition","iris scan"],C),
    ]),
    "dna": ("DNA identification", [
      ("dna-forensic","Forensic DNA","Laboratory forensic DNA profiling.",["DNA profiling","CODIS"],C),
      ("rapid-dna","Rapid DNA","Field/booking rapid DNA analysis.",["Rapid DNA","booking DNA"],C),
    ]),
    "other-biometric": ("Other biometrics", [
      ("tattoo-recognition","Tattoo recognition","Identifies/matches by tattoo imagery.",["tattoo recognition","tattoo matching"],C),
      ("gait-recognition","Gait recognition","Identifies by walking gait.",["gait recognition","gait analysis"],C),
      ("voice-recognition","Voice recognition","Identifies by voiceprint.",["voice recognition","speaker identification","voiceprint"],C),
    ]),
  }),
  "acoustic": ("Acoustic sensing", {
    "gunshot-detection": ("Gunshot detection", [
      ("gunshot-detection-fixed","Gunshot detection","Acoustic sensors localising gunfire.",["gunshot detection","acoustic gunshot"],H),
    ]),
    "acoustic-sensing": ("General acoustic sensing", [
      ("acoustic-sensing-general","Acoustic sensing","Non-gunshot acoustic monitoring/classification.",["acoustic sensor","sound monitoring"],M),
    ]),
  }),
  "robotics-aerial": ("Aerial robotics", {
    "uas": ("Unmanned aerial systems", [
      ("uas-general","Unmanned aerial system","A drone operated for surveillance tasks.",["UAS","drone","UAV"],H),
      ("drone-as-first-responder","Drone as first responder","Autonomous/rapid-launch drone dispatched to calls.",["DFR","drone as first responder"],H),
    ]),
    "aerostat": ("Aerostats and persistent aerial", [
      ("tethered-aerostat","Tethered aerostat","A tethered balloon carrying sensors.",["aerostat","tethered balloon"],H),
      ("persistent-aerial-surveillance","Persistent aerial surveillance","Wide-area, long-dwell aerial imaging.",["persistent surveillance","wide-area motion imagery","WAMI"],C),
    ]),
  }),
  "robotics-ground": ("Ground robotics", {
    "ground-robotics": ("Ground robotics", [
      ("ugv","Unmanned ground vehicle","A ground robot carrying sensors.",["UGV","ground robot"],M),
      ("robot-dog","Quadruped robot","A legged robot platform (e.g. quadruped).",["robot dog","quadruped robot"],M),
    ]),
  }),
  "comms-intercept": ("Communications interception", {
    "cell-site-simulator": ("Cell-site simulators", [
      ("cell-site-simulator-general","Cell-site simulator","Simulates a cell tower to locate/identify handsets.",["cell-site simulator","IMSI catcher"],C),
    ]),
    "lawful-intercept": ("Lawful intercept and metadata", [
      ("wiretap-content","Content interception","Interception of communications content.",["wiretap","content interception","Title III"],C),
      ("metadata-interception","Metadata interception","Collection of communications metadata.",["pen register","trap and trace","metadata"],C),
      ("tower-dump","Tower dump","Bulk request of all handsets seen by a tower in a window.",["tower dump","cell tower dump"],C),
    ]),
    "wifi-bluetooth-tracking": ("Wi-Fi / Bluetooth tracking", [
      ("wifi-bluetooth-sensor","Wi-Fi/Bluetooth sensor","Detects/tracks devices by Wi-Fi/Bluetooth radio emissions.",["wifi tracking","bluetooth beacon","MAC address sensor"],H),
    ]),
  }),
  "device-forensics": ("Mobile device forensics", {
    "mobile-forensics": ("Mobile device forensics", [
      ("extraction-logical","Logical extraction","Logical acquisition of accessible device data.",["logical extraction"],C),
      ("extraction-physical","Physical extraction","Bit-level physical acquisition of device storage.",["physical extraction","full file system"],C),
      ("cloud-account-extraction","Cloud-account extraction","Acquisition of cloud account data via tokens/credentials.",["cloud extraction","cloud analyzer"],C),
      ("exploit-service","Exploit service","Vendor exploit service to unlock/extract devices.",["exploit service","device unlock"],C),
    ]),
  }),
  "data-acquisition": ("Commercial data acquisition", {
    "location-data": ("Location-data acquisition", [
      ("adtech-location-purchase","Ad-tech location purchase","Purchase of advertising-derived device location data.",["ad-tech location","mobile advertising ID"],C),
      ("location-data-subscription","Location-data subscription platform","Subscription platform for querying device location history.",["location data platform","location intelligence"],C),
      ("geofence-warrant-data","Geofence data","Location data obtained via geofence process.",["geofence warrant","reverse location"],C),
    ]),
    "records-broker": ("Person- and utility-records brokers", [
      ("person-records-broker","Person-records broker","Commercial broker of person records (addresses, associates).",["data broker","person search"],C),
      ("utility-records","Utility records","Access to utility subscriber records.",["utility records","utility subpoena"],H),
    ]),
  }),
  "analytics-inference": ("Analytics and inference", {
    "predictive-policing": ("Predictive policing", [
      ("predictive-policing-place","Place-based predictive policing","Predicts where crime will occur.",["predictive policing","hot spot"],H),
      ("predictive-policing-person","Person-based predictive policing","Predicts who will be involved in crime.",["person-based prediction","heat list","risk list"],C),
    ]),
    "risk-analytics": ("Risk and behavioural analytics", [
      ("risk-assessment","Risk assessment","Algorithmic risk scoring of individuals.",["risk assessment","risk score","pretrial risk"],C),
      ("behavioral-analytics","Behavioural analytics","Detects anomalous behaviour patterns.",["behavioral analytics","anomaly detection"],H),
    ]),
    "osint-monitoring": ("OSINT and social-media monitoring", [
      ("social-media-monitoring","Social-media monitoring","Monitors social media for people/events.",["social media monitoring","SMM"],C),
      ("osint-platform","OSINT platform","Aggregated open-source intelligence tooling.",["OSINT platform","open source intelligence"],H),
    ]),
  }),
  "integration-platform": ("Integration platforms", {
    "rtcc": ("Real-time crime centre platform", [
      ("rtcc-platform","RTCC platform","Software surface aggregating feeds for a real-time crime centre (the software; the unit is an Organization sub-type, SIG-ONTO-057).",["RTCC","real-time crime center","fusion platform"],H),
    ]),
    "cad-rms": ("CAD/RMS integration", [
      ("cad-rms-integration","CAD/RMS integration","Integrates computer-aided dispatch / records management data.",["CAD integration","RMS integration"],M),
    ]),
    "federation-hub": ("Camera federation hub", [
      ("camera-federation-hub","Camera federation hub","Federates many camera systems into one search surface.",["camera federation","video hub"],H),
    ]),
    "investigative-platform": ("Third-party investigative platform", [
      ("third-party-investigative-platform","Third-party investigative platform","Aggregated investigative analytics over multiple data sources.",["investigative platform","link analysis"],C),
    ]),
  }),
  "person-monitoring": ("Person monitoring", {
    "electronic-monitoring": ("Electronic monitoring", [
      ("electronic-monitoring-ankle","Electronic monitoring","GPS/RF monitoring of a supervised person.",["electronic monitoring","ankle monitor","GPS monitoring"],C),
    ]),
    "custodial-monitoring": ("Custodial communications monitoring", [
      ("jail-communications-monitoring","Jail-communications monitoring","Monitoring/analysis of custodial phone/messaging.",["jail calls","inmate communications","call monitoring"],C),
    ]),
  }),
  "facility-screening": ("Facility screening", {
    "weapon-detection": ("Weapon detection", [
      ("weapon-detection-scanner","Weapon detection","Automated weapon/threat detection at a portal.",["weapon detection","concealed weapon"],H),
    ]),
    "school-surveillance": ("School surveillance", [
      ("school-surveillance-suite","School surveillance","Surveillance/monitoring suite deployed in schools.",["school surveillance","student monitoring"],C),
    ]),
  }),
}
def build():
  domains=[]; fam=0; tech=0
  for ds,(dl,fams) in TAX.items():
    families=[]
    for fs,(fl,techs) in fams.items():
      fam+=1; leaves=[]
      for ts,tl,cr,sg,sa in techs:
        leaves.append({"slug":ts,"label":tl,"distinguishing_criterion":cr,"evidence_signature":sg,"salience":sa}); tech+=1
      leaves.append({"slug":f"{fs}-unspecified","label":f"{fl} (unspecified)","distinguishing_criterion":"The coarsest level: evidence names the family but not the discriminator separating its specific technologies.","evidence_signature":[fl.lower()],"salience":(max((t[4] for t in techs),key="LMHC".index) if techs else M)}); tech+=1
      families.append({"slug":fs,"label":fl,"technologies":leaves})
    domains.append({"slug":ds,"label":dl,"families":families})
  return {"scheme":"technology","title":"SIG technology vocabulary (\u00a713.1)","version":"1.0.0","hierarchy":"domain \u2192 family \u2192 technology","counts":{"domains":len(domains),"families":fam,"technologies":tech},"domains":domains}
doc=build(); print("counts:",doc["counts"])
assert doc["counts"]=={"domains":14,"families":36,"technologies":104},doc["counts"]
header=("# SPDX-License-Identifier: Apache-2.0\n# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation\n# carry per-artifact licences \u2014 see LICENSE and docs/2_canonical_design_spec.md \u00a742.\n#\n# The SIG technology vocabulary (\u00a713.1) \u2014 SKOS source of truth. 14 domains, 36\n# families, 104 technologies; every family carries an -unspecified leaf\n# (SIG-ONTO-020/054); every technology carries a distinguishing criterion, an\n# evidence signature, and a salience L/M/H/C (SIG-ONTO-056). Slugs are\n# lowercase-hyphenated, stable forever, encode family-discriminator, never a\n# vendor (SIG-ONTO-053/055). Authored source; the SKOS artifact is generated from it.\n")
pathlib.Path("ontology/vocab/technology.yaml").write_text(header+yaml.safe_dump(doc,sort_keys=False,allow_unicode=True,width=100))
print("wrote ontology/vocab/technology.yaml")
