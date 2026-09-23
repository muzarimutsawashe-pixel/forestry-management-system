# -*- coding: utf-8 -*-
# ============================================================
# AI CHATBOT - 5-Provider Fallback Edition
# Groq + Cerebras + SambaNova + Mistral + Gemini
# ============================================================

import os, json, re, time, random
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import text

load_dotenv()

# ============================================================
# PROVIDER CONFIGURATION
# ============================================================

PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1",
        "model": "groq/compound",
        "key": os.getenv("GROQ_API_KEY"),
    },
    {
        "name": "Cerebras",
        "url": "https://api.cerebras.ai/v1",
        "model": "llama-3.3-70b",
        "key": os.getenv("CEREBRAS_API_KEY"),
    },
    {
        "name": "SambaNova",
        "url": "https://api.sambanova.ai/v1",
        "model": "Meta-Llama-3.3-70B-Instruct",
        "key": os.getenv("SAMBANOVA_API_KEY"),
    },
    {
        "name": "Mistral",
        "url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
        "key": os.getenv("MISTRAL_API_KEY"),
    },
    {
        "name": "Gemini",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-3.6-flash",
        "key": os.getenv("GEMINI_API_KEY"),
    },
]

_clients = []
for _p in PROVIDERS:
    if _p["key"]:
        _clients.append({
            "name": _p["name"],
            "model": _p["model"],
            "client": OpenAI(api_key=_p["key"], base_url=_p["url"],
                             timeout=60.0, max_retries=0),
        })

if not _clients:
    print("[chatbot] WARNING: No AI provider keys found in .env")
else:
    print(f"[chatbot] Loaded providers: {[c['name'] for c in _clients]}")


# ============================================================
# KNOWLEDGE BASE
# ============================================================

SPECIES = {
 "Pinus patula": {
   "common":"Patula pine","sawlog_yr":(24,30),"pulp_yr":(15,25),
   "init_sph":1400,"final_sph":400,"dbh_cm":45,"mai":(16,26),
   "prune":[{"yr":(4,6),"h":2.5},{"yr":(7,9),"h":5.0},{"yr":(10,12),"h":7.5},{"yr":(12,14),"h":10.0}],
   "thin":[{"yr":(6,8),"sph":650},{"yr":(12,15),"sph":400}],
   "weeding":[{"yr":(0,1)},{"yr":(1,2)},{"yr":(2,3)}],
   "site":"Alt>1200m, rain>1000mm","pest":"Pineus aphid; Armillaria; Rhizina",
   "note":"Dominant ZW softwood. 30-yr conventional, 24-yr financial optimum."},
 "Pinus elliottii": {
   "common":"Slash pine","sawlog_yr":(20,30),"pulp_yr":(15,18),
   "init_sph":1400,"final_sph":300,"dbh_cm":45,"mai":(14,22),
   "prune":[{"yr":(5,7),"h":2.5},{"yr":(8,10),"h":5.0}],
   "thin":[{"yr":(8,10),"sph":750},{"yr":(13,15),"sph":500},{"yr":(17,20),"sph":300}],
   "weeding":[{"yr":(0,1)},{"yr":(1,2)},{"yr":(2,3)}],
   "site":"Lower-alt, poor sites","pest":"Rhizina (do NOT burn); hail when young",
   "note":"Drought-tolerant; good for marginal sites."},
 "Pinus taeda": {
   "common":"Loblolly pine","sawlog_yr":(20,25),"pulp_yr":(12,16),
   "init_sph":1400,"final_sph":400,"dbh_cm":40,"mai":(16,26),
   "prune":[{"yr":(5,7),"h":2.5},{"yr":(8,10),"h":5.0}],
   "thin":[{"yr":(7,10),"sph":700},{"yr":(13,16),"sph":400}],
   "weeding":[{"yr":(0,1)},{"yr":(1,2)},{"yr":(2,3)}],
   "site":"Warm lower-alt","pest":"Fusiform rust",
   "note":"Higher-quality timber than P. patula."},
 "Eucalyptus cloeziana": {
   "common":"Gympie messmate","sawlog_yr":(12,16),"pole_yr":(10,12),"coppice_yr":(6,12),
   "init_sph":1100,"final_sph":600,"dbh_cm":20,"mai":(20,30),
   "prune":[{"yr":(2,3),"h":2.0}],
   "thin":[{"yr":(4,5),"sph":600}],
   "weeding":[{"yr":(0,1)},{"yr":(1,2)}],
   "site":"Warm, 1000-1500mm rain","pest":"Resistant; best stem form",
   "note":">30 m3/ha/yr ZW. Best transmission poles. Cut at 12 yr."},
 "Eucalyptus grandis": {
   "common":"Rose gum","sawlog_yr":(14,30),"pole_yr":(10,14),"pulp_yr":(6,10),
   "init_sph":1333,"final_sph":250,"dbh_cm":20,"mai":(15,55),
   "prune":[{"yr":(1,2),"h":2.0}],
   "thin":[{"yr":(7,8),"sph":400},{"yr":(10,12),"sph":250}],
   "weeding":[{"yr":(0,1)},{"yr":(1,2)}],
   "site":"Deep soils, summer rain","pest":"Leptocybe wilt; Gonipterus",
   "note":"72% poles, 28% pulp from recovered volume."},
 "Poplar": {
   "common":"Poplar","sawlog_yr":(15,25),"pulp_yr":(10,15),
   "init_sph":400,"final_sph":400,"dbh_cm":30,"mai":(8,15),
   "prune":[],"thin":[],"weeding":[{"yr":(0,1)},{"yr":(1,2)}],
   "site":"Moist alluvial","pest":"Borers; leaf rust",
   "note":"Historic match industry. 4x4m to 6x6m."},
 "Wattle": {
   "common":"Black wattle","bark_yr":(7,10),"timber_yr":(10,15),
   "init_sph":1300,"final_sph":600,"mai":(8,15),
   "prune":[],"thin":[],"weeding":[{"yr":(0,1)}],
   "site":"800-1200mm rain","pest":"Hardy",
   "note":"30-40% tannin in bark."},
}

ZW_REGIMES = {
 "Pine sawlog":{"rot":25,"thin_yr":[13,18],"note":"TPF standard"},
 "Pine pulp":{"rot":14,"thin_yr":[],"note":"Plus sawlog thinnings"},
 "Euc transmission poles":{"rot":11,"thin_yr":[],"note":"Border Timbers, 10-12 yr"},
 "Euc light poles":{"rot":5,"thin_yr":[],"note":"4-6 yr"},
 "Wattle extract":{"rot":10,"thin_yr":[],"note":"Bark at 7 yr"},
 "Poplar":{"rot":10,"thin_yr":[],"note":"Historic match regime"},
}

REFERENCE = {
 "mai":{"pine":"16-26 m3/ha/yr","euc_sa_avg":"21 (range 15-55)","euc_zw":"30+ for E.cloeziana"},
 "fire":{"break_width":"10 m min","burn_month":"May-June","hazard_index":"0-39 green, 39-59 orange, >59 red","rhizina":"Do NOT burn P.elliottii slash"},
 "invasive":{"name":"Vernonanthura polyanthes (Mupese pese)","origin":"Brazil 1990s via Mozambique","habitat":"Disturbed/burnt; 345-1710m","control":"Triclopyr experimental; Garlon suppresses","cost":"~USD 100k/yr control in E.Highlands"},
 "pests":{"Pineus":"P. patula","Rhizina":"post-fire pines","Armillaria":"old agri land","Leptocybe":"Euc wilt","Gonipterus":"Euc weevil","Fusiform":"P. taeda"},
 "harvest":{"pine_sawlog":"24-30 yr, DBH 40cm, top 23cm","pine_pulp":"14-18 yr","euc_poles":"10-12 yr, DBH 18-20cm","euc_pulp":"6-10 yr","wattle_bark":"7-10 yr"},
 "nursery":{"seed":"Forestry Commission Tree Seed Centre","genetics":"40+ yr improvement; 33 BSOs","fert":"NPK 2:3:2 @ 0.5 g/plant"},
 "timber_grades":{"standard":"ZWS 257 Parts 1-5","sawlog_top_dia":"23 cm min"},
 "regulations":{"forestry_act":"Ch 19:05 - felling permits","ema":"EMA Act Ch 20:27","fire_si":"SI 7 of 2007; SI 116 of 2012"},
 "weeds":{"manual":"total/spot/ring weeding","chemical":"Triclopyr, Glyphosate, Tordon 22K"},
 "growth":{"P_patula_24yr":"175m3/ha, IRR 7.7%","P_patula_30yr":"229m3/ha, IRR 6.6%"},
}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """AI assistant for Allied Timbers Zimbabwe Forestry.

ROLE: {role}  ESTATE: {estate}

RULES:
1. DB numbers must come from a tool result THIS turn. Never invent.
2. Forestry standards from species_params / standards / zw_regimes tools.
3. "What's due/overdue/next" -> use assess_status / gap_analysis / work_plan / harvest_ready.
4. Empty tool result: say so.

BREVITY (IMPORTANT):
- Keep answers to 3-5 sentences unless a list is genuinely needed.
- For lists: max 5 items. Summarize instead of long tables.
- No multi-section reports unless the user explicitly asks for a "report".
- Skip preamble and closing pleasantries.
- Cite the standard briefly: "age 4-6 (Crockford & Bgoni 1992)".
- If the user asks "how many" give the number plus one supporting detail.
- If the user asks "which", list up to 5 codes then say "and N more".

Format dates DD/MM/YYYY. For map requests, call map_action.
"""


# ============================================================
# TOOL SCHEMAS
# ============================================================

def _fn(n, d, p, r=None):
    return {"type":"function","function":{"name":n,"description":d,
            "parameters":{"type":"object","properties":p,"required":r or []}}}

TOOLS = [
 _fn("estate_kpis","KPI summary for an estate.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("find_compartments","Search compartments by code/species/block/year/age.",
     {"estate_id":{"type":"integer"},"query":{"type":"string"},
      "species":{"type":"string"},"block":{"type":"string"},
      "min_planting_year":{"type":"integer"},"max_planting_year":{"type":"integer"},
      "min_age":{"type":"integer"},"max_age":{"type":"integer"}},["estate_id"]),
 _fn("compartment","Full details for one compartment.",
     {"code":{"type":"string"},"estate_id":{"type":"integer"}},["code"]),
 _fn("compartment_history","All silviculture ops for a compartment.",
     {"code":{"type":"string"},"estate_id":{"type":"integer"}},["code"]),
 _fn("list_estates","Estates the user can see.",{}),
 _fn("species_breakdown","Species composition with areas and %.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("block_breakdown","Block totals: compartments, area, avg age.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("age_distribution","Age-class distribution (0-5, 5-10, 10-15, ...).",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("planting_histogram","Planted area per planting year.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("compare_blocks","Side-by-side block comparison.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("operation_coverage","How many compartments have each operation type recorded.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("find_missing_operations",
     "Compartments that SHOULD have received a specific operation but have none recorded.",
     {"estate_id":{"type":"integer"},
      "operation":{"type":"string","enum":["weeding","prune","thin","planting"]}},["estate_id","operation"]),
 _fn("gap_analysis","Full silvicultural gap per compartment.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("assess_status","Compare compartments to standard schedules; flags due/overdue.",
     {"estate_id":{"type":"integer"},
      "focus":{"type":"string","enum":["all","harvest","thin","prune"]}},["estate_id"]),
 _fn("harvest_ready",
     "Single-call answer: which compartments are at or past their harvest rotation.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("work_plan","Prioritised 12-month action plan.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("stand_metrics","Estimate standing volume & years to harvest.",
     {"code":{"type":"string"},"estate_id":{"type":"integer"}},["code"]),
 _fn("explain_compartment","Narrative explanation of one compartment.",
     {"code":{"type":"string"},"estate_id":{"type":"integer"}},["code"]),
 _fn("spatial_in_block","Compartments inside a block.",
     {"block":{"type":"string"},"estate_id":{"type":"integer"}},["block"]),
 _fn("spatial_neighbours","Compartments that share a boundary with the given one.",
     {"code":{"type":"string"},"estate_id":{"type":"integer"}},["code"]),
 _fn("spatial_near","Compartments within X metres of the given one.",
     {"code":{"type":"string"},"metres":{"type":"integer"},"estate_id":{"type":"integer"}},["code","metres"]),
 _fn("spatial_area_summary","Total area of a set of compartments.",
     {"estate_id":{"type":"integer"},"block":{"type":"string"},
      "species":{"type":"string"},"planting_year":{"type":"integer"}},["estate_id"]),
 _fn("geometry_inventory","How many compartments have polygons; SRID check.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("map_action","Return codes so the frontend highlights compartments on the map.",
     {"compartment_codes":{"type":"array","items":{"type":"string"}},
      "zoom_to":{"type":"string"},"label":{"type":"string"}},["compartment_codes"]),
 _fn("generate_estate_report","Full professional report for an estate.",
     {"estate_id":{"type":"integer"}},["estate_id"]),
 _fn("generate_compartment_report","Detailed report for one compartment.",
     {"code":{"type":"string"},"estate_id":{"type":"integer"}},["code"]),
 _fn("get_species_parameters","Silviculture parameters for a species.",
     {"species":{"type":"string"}},["species"]),
 _fn("get_forestry_standards","Reference topics.",
     {"topic":{"type":"string"}}),
 _fn("get_zw_regimes","Zimbabwe TPF standard regimes.",{}),
]


# ============================================================
# HELPERS
# ============================================================

MAX_FINDINGS = 10
MAX_ACTIONS  = 20
MAX_SEARCH   = 25

def _norm(code):
    if not code: return ""
    return re.sub(r"^([A-Za-z]+)0*(\d+)([A-Za-z]?)$","\\1\\2\\3",
                  code.strip().replace(" ",""))

def _eid(user, req):
    if user["role"] in ("production_manager","admin"):
        return int(req) if req else 11
    return int(user["estate_id"])

def _skey(raw):
    if not raw: return None
    r = raw.strip().lower().replace(" ","")
    for k in SPECIES:
        if k.lower().replace(" ","") == r: return k
    if "patula" in r: return "Pinus patula"
    if "elliottii" in r or "elliotti" in r: return "Pinus elliottii"
    if "taeda" in r: return "Pinus taeda"
    if "cloeziana" in r: return "Eucalyptus cloeziana"
    if "grandis" in r: return "Eucalyptus grandis"
    if "poplar" in r: return "Poplar"
    if "wattle" in r or "mearnsii" in r: return "Wattle"
    return None


# ============================================================
# DB QUERY TOOLS
# ============================================================

def _estate_kpis(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    r = db.execute(text("""SELECT COUNT(*) c, COALESCE(SUM(area_planted),0) a,
        COALESCE(ROUND(AVG(age),1),0) g, COUNT(DISTINCT species) s
        FROM compartments WHERE estate_id=:e"""),{"e":eid}).mappings().first()
    n = db.execute(text("SELECT estate_name FROM estates WHERE estate_id=:e"),
                   {"e":eid}).scalar() or f"Estate {eid}"
    return {"estate":n,"compartments":int(r["c"]),"total_area_ha":round(float(r["a"]),1),
            "avg_age":float(r["g"]),"species":int(r["s"])}

def _find_compartments(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    sql = """SELECT compartment_code cc, species sp, planting_year py, age,
             area_planted ar, block_id blk FROM compartments WHERE estate_id=:e"""
    p = {"e":eid}
    q = (a.get("query") or "").strip().lower()
    if q:
        sql += " AND (LOWER(compartment_code) LIKE :q OR LOWER(COALESCE(species,'')) LIKE :q OR LOWER(COALESCE(block_id,'')) LIKE :q)"
        p["q"] = f"%{q}%"
    for k,c in [("species","species ILIKE :sp"),("block","UPPER(block_id)=:blk"),
                ("min_planting_year","planting_year>=:mnp"),("max_planting_year","planting_year<=:mxp"),
                ("min_age","age>=:mna"),("max_age","age<=:mxa")]:
        if a.get(k) is not None:
            sql += f" AND {c}"; p[k]=a[k]
    sql += f" ORDER BY compartment_code LIMIT {MAX_SEARCH}"
    rows = db.execute(text(sql),p).mappings().all()
    return {"n":len(rows),"codes":[r["cc"] for r in rows],
            "items":[{"c":r["cc"],"sp":r["sp"],"yr":r["py"],"age":r["age"],
                      "ha":round(float(r["ar"]),2) if r["ar"] else None,"blk":r["blk"]}
                     for r in rows]}

def _compartment(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    code = _norm(a["code"])
    r = db.execute(text("""SELECT compartment_code cc, species sp, planting_year py, age,
        area_planted ar, area_compartment ac, block_id blk, status st
        FROM compartments WHERE estate_id=:e
        AND regexp_replace(regexp_replace(trim(compartment_code),'\\s+','','g'),
            '^([A-Za-z]+)0*([0-9]+)([A-Za-z]?)$','\\1\\2\\3')=:c LIMIT 1"""),
        {"e":eid,"c":code}).mappings().first()
    if not r: return {"found":False,"code":code}
    return {"found":True,"code":r["cc"],"sp":r["sp"],"yr":r["py"],"age":r["age"],
            "ha_planted":float(r["ar"]) if r["ar"] else None,
            "ha_total":float(r["ac"]) if r["ac"] else None,
            "blk":r["blk"],"status":r["st"]}

def _compartment_history(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    code = _norm(a["code"])
    rows = db.execute(text("""SELECT so.operation_type op, so.operation_date_display dt,
        so.area_treated ar, so.status st, so.remarks rm
        FROM silviculture_operations so JOIN compartments c ON c.compartment_id=so.compartment_id
        WHERE c.estate_id=:e AND regexp_replace(regexp_replace(trim(c.compartment_code),'\\s+','','g'),
            '^([A-Za-z]+)0*([0-9]+)([A-Za-z]?)$','\\1\\2\\3')=:c
        ORDER BY so.operation_date NULLS LAST, so.operation_type LIMIT 30"""),
        {"e":eid,"c":code}).mappings().all()
    return {"code":code,"n":len(rows),"ops":[
        {"op":r["op"],"dt":r["dt"] or "-","ha":float(r["ar"]) if r["ar"] else None,
         "st":r["st"],"rm":r["rm"]} for r in rows]}

def _list_estates(db, user, a):
    if user["role"] in ("production_manager","admin"):
        rows = db.execute(text("SELECT estate_id, estate_name FROM estates ORDER BY estate_id")).mappings().all()
    else:
        rows = db.execute(text("SELECT estate_id, estate_name FROM estates WHERE estate_id=:e"),
                          {"e":user["estate_id"]}).mappings().all()
    return {"estates":[{"id":r["estate_id"],"name":r["estate_name"]} for r in rows]}


# ============================================================
# ANALYSIS TOOLS
# ============================================================

def _species_breakdown(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    rows = db.execute(text("""SELECT species sp, COUNT(*) n, COALESCE(SUM(area_planted),0) ar
        FROM compartments WHERE estate_id=:e AND species IS NOT NULL
        GROUP BY species ORDER BY ar DESC"""),{"e":eid}).mappings().all()
    total = sum(float(r["ar"]) for r in rows) or 1
    return {"total_ha":round(total,1),"items":[
        {"sp":r["sp"],"n":int(r["n"]),"ha":round(float(r["ar"]),1),
         "pct":round(float(r["ar"])/total*100,1)} for r in rows]}

def _block_breakdown(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    rows = db.execute(text("""SELECT COALESCE(block_id,'?') blk, COUNT(*) n,
        COALESCE(SUM(area_planted),0) ar, COALESCE(ROUND(AVG(age),1),0) g
        FROM compartments WHERE estate_id=:e GROUP BY blk ORDER BY ar DESC"""),
        {"e":eid}).mappings().all()
    return {"n":len(rows),"blocks":[
        {"blk":r["blk"],"n":int(r["n"]),"ha":round(float(r["ar"]),1),"avg_age":float(r["g"])}
        for r in rows]}

def _age_distribution(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    rows = db.execute(text("""
        SELECT
          CASE
            WHEN age < 5 THEN '0-5'
            WHEN age < 10 THEN '5-10'
            WHEN age < 15 THEN '10-15'
            WHEN age < 20 THEN '15-20'
            WHEN age < 30 THEN '20-30'
            ELSE '30+'
          END AS bucket,
          COUNT(*) n, COALESCE(SUM(area_planted),0) ar
        FROM compartments WHERE estate_id=:e AND age IS NOT NULL
        GROUP BY bucket
    """),{"e":eid}).mappings().all()
    order = ["0-5","5-10","10-15","15-20","20-30","30+"]
    bucket_map = {r["bucket"]:r for r in rows}
    return {"classes":[
        {"class":b,"n":int(bucket_map[b]["n"]) if b in bucket_map else 0,
         "ha":round(float(bucket_map[b]["ar"]),1) if b in bucket_map else 0}
        for b in order]}

def _planting_histogram(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    rows = db.execute(text("""SELECT planting_year yr, COUNT(*) n,
        COALESCE(SUM(area_planted),0) ar FROM compartments
        WHERE estate_id=:e AND planting_year IS NOT NULL
        GROUP BY yr ORDER BY yr DESC LIMIT 40"""),{"e":eid}).mappings().all()
    return {"years":[{"yr":int(r["yr"]),"n":int(r["n"]),"ha":round(float(r["ar"]),1)}
                     for r in rows]}

def _compare_blocks(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    rows = db.execute(text("""SELECT COALESCE(block_id,'?') blk,
        COUNT(*) n, COALESCE(SUM(area_planted),0) ar,
        COALESCE(ROUND(AVG(age),1),0) g,
        COUNT(DISTINCT species) sp_count
        FROM compartments WHERE estate_id=:e GROUP BY blk ORDER BY ar DESC"""),
        {"e":eid}).mappings().all()
    return {"comparison":[{"blk":r["blk"],"n":int(r["n"]),
                           "ha":round(float(r["ar"]),1),"avg_age":float(r["g"]),
                           "species":int(r["sp_count"])} for r in rows]}

def _operation_coverage(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    total = db.execute(text("SELECT COUNT(*) FROM compartments WHERE estate_id=:e"),
                       {"e":eid}).scalar() or 0
    rows = db.execute(text("""SELECT so.operation_type op,
        COUNT(DISTINCT c.compartment_id) n
        FROM silviculture_operations so
        JOIN compartments c ON c.compartment_id=so.compartment_id
        WHERE c.estate_id=:e GROUP BY op ORDER BY n DESC"""),
        {"e":eid}).mappings().all()
    return {"total_compartments":int(total),"coverage":[
        {"op":r["op"],"n":int(r["n"]),
         "pct":round(int(r["n"])/int(total)*100,1) if total else 0}
        for r in rows]}


# ============================================================
# GAP / OVERDUE TOOLS
# ============================================================

def _find_missing_operations(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    op_type = (a.get("operation") or "").lower()

    rows = db.execute(text("""
        SELECT c.compartment_code cc, c.species sp, c.age, c.area_planted ar,
        COALESCE((SELECT COUNT(*) FROM silviculture_operations so
                  WHERE so.compartment_id=c.compartment_id
                  AND LOWER(so.operation_type) LIKE :op), 0) op_count
        FROM compartments c WHERE c.estate_id=:e ORDER BY c.compartment_code
    """), {"e":eid,"op":f"%{op_type}%"}).mappings().all()

    missing = []
    for r in rows:
        if r["age"] is None or r["op_count"] > 0: continue
        k = _skey(r["sp"])
        if not k: continue
        p = SPECIES[k]
        schedule_key = {"weeding":"weeding","prune":"prune","thin":"thin"}.get(op_type)
        if not schedule_key: continue
        sched = p.get(schedule_key, [])
        for s in sched:
            lo, hi = s.get("yr",(0,0))
            if r["age"] > hi:
                missing.append({
                    "c":r["cc"],"sp":k,"age":r["age"],
                    "ha":round(float(r["ar"]),1) if r["ar"] else 0,
                    "expected_at":f"{lo}-{hi}",
                    "overdue_by_yr":r["age"]-hi,
                })
                break
    missing.sort(key=lambda x: -x["overdue_by_yr"])
    return {"operation":op_type,"total_missing":len(missing),
            "compartments":missing[:MAX_FINDINGS]}

def _gap_analysis(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    rows = db.execute(text("""
        SELECT c.compartment_code cc, c.species sp, c.age,
        COALESCE((SELECT json_agg(LOWER(so.operation_type))
            FROM silviculture_operations so WHERE so.compartment_id=c.compartment_id),
            '[]'::json) ops
        FROM compartments c WHERE c.estate_id=:e ORDER BY c.compartment_code
    """), {"e":eid}).mappings().all()

    gaps = []
    for r in rows:
        age = r["age"]; k = _skey(r["sp"])
        if age is None or not k: continue
        p = SPECIES[k]
        ops_done = " ".join(str(o) for o in (r["ops"] or [])).lower()

        missing = []
        for w in p.get("weeding", []):
            lo, hi = w["yr"]
            if age > hi and "weed" not in ops_done:
                missing.append(f"weeding ({lo}-{hi} yr)")
        for pr in p.get("prune", []):
            lo, hi = pr["yr"]
            if age > hi and "prune" not in ops_done:
                missing.append(f"prune to {pr['h']}m ({lo}-{hi} yr)")
        for t in p.get("thin", []):
            lo, hi = t["yr"]
            if age > hi and "thin" not in ops_done:
                missing.append(f"thin to {t['sph']} sph ({lo}-{hi} yr)")

        if missing:
            gaps.append({"c":r["cc"],"sp":k,"age":age,"missing":missing})

    return {"compartments_with_gaps":len(gaps),"total":len(rows),
            "gaps":gaps[:MAX_FINDINGS]}

def _assess_status(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    focus = a.get("focus","all")
    rows = db.execute(text("""
        SELECT c.compartment_code cc, c.species sp, c.age, c.area_planted ar,
        COALESCE((SELECT json_agg(so.operation_type)
            FROM silviculture_operations so WHERE so.compartment_id=c.compartment_id),
            '[]'::json) ops
        FROM compartments c WHERE c.estate_id=:e ORDER BY c.compartment_code"""),
        {"e":eid}).mappings().all()

    out = {"harvest_overdue":[],"harvest_due":[],
           "thin_overdue":[],"thin_due":[],
           "prune_overdue":[],"prune_due":[],"unmapped":[]}

    for r in rows:
        age = r["age"]; k = _skey(r["sp"])
        if age is None: continue
        if not k:
            out["unmapped"].append({"c":r["cc"],"sp":r["sp"]})
            continue
        p = SPECIES[k]; ops = [str(o).lower() for o in (r["ops"] or [])]
        entry = {"c":r["cc"],"sp":k,"age":age,
                 "ha":round(float(r["ar"]),1) if r["ar"] else 0}

        if focus in ("all","harvest"):
            rot = p.get("sawlog_yr") or p.get("pole_yr")
            if rot:
                lo,hi = rot
                if age > hi: out["harvest_overdue"].append({**entry,"rot":f"{lo}-{hi}","over":age-hi})
                elif age >= lo: out["harvest_due"].append({**entry,"rot":f"{lo}-{hi}"})

        if focus in ("all","thin"):
            for t in p.get("thin",[]):
                lo,hi = t["yr"]
                done = any("thin" in o for o in ops)
                if age > hi and not done:
                    out["thin_overdue"].append({**entry,"expected":f"{lo}-{hi}","sph":t["sph"]})
                elif lo <= age <= hi and not done:
                    out["thin_due"].append({**entry,"expected":f"{lo}-{hi}","sph":t["sph"]})

        if focus in ("all","prune"):
            for pr in p.get("prune",[]):
                lo,hi = pr["yr"]
                done = any("prune" in o for o in ops)
                if age > hi and not done:
                    out["prune_overdue"].append({**entry,"expected":f"{lo}-{hi}","h":pr["h"]})
                elif lo <= age <= hi and not done:
                    out["prune_due"].append({**entry,"expected":f"{lo}-{hi}","h":pr["h"]})

    counts = {k:len(v) for k,v in out.items()}
    capped = {k:v[:MAX_FINDINGS] for k,v in out.items()}
    return {"checked":len(rows),"focus":focus,"counts":counts,"findings":capped}

def _harvest_ready(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    rows = db.execute(text("""
        SELECT compartment_code cc, species sp, age, area_planted ar, block_id blk
        FROM compartments WHERE estate_id=:e AND age IS NOT NULL
        ORDER BY age DESC
    """), {"e":eid}).mappings().all()

    ready, overdue = [], []
    for r in rows:
        k = _skey(r["sp"])
        if not k: continue
        p = SPECIES[k]
        rot = p.get("sawlog_yr") or p.get("pole_yr")
        if not rot: continue
        lo, hi = rot
        entry = {"c": r["cc"], "sp": k, "age": r["age"],
                 "ha": round(float(r["ar"]),1) if r["ar"] else 0,
                 "blk": r["blk"], "rotation": f"{lo}-{hi} yr"}
        if r["age"] > hi:
            overdue.append({**entry, "over_by_yr": r["age"] - hi})
        elif r["age"] >= lo:
            ready.append(entry)

    return {
        "overdue_count": len(overdue),
        "ready_count":  len(ready),
        "overdue_compartments": overdue[:15],
        "ready_compartments":   ready[:15],
        "note": "Based on sawlog or pole rotation window from species standards.",
    }

def _work_plan(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    s = _assess_status(db, user, {"estate_id":eid,"focus":"all"})
    f = s["findings"]
    plan = []
    for i in f["harvest_overdue"]:
        plan.append({"p":1,"act":"HARVEST (overdue)","c":i["c"],"sp":i["sp"],"age":i["age"],
                     "why":f"age {i['age']} > rot {i['rot']}"})
    for i in f["harvest_due"]:
        plan.append({"p":2,"act":"plan harvest","c":i["c"],"sp":i["sp"],"age":i["age"],
                     "why":f"age {i['age']} in rot {i['rot']}"})
    for i in f["thin_overdue"]:
        plan.append({"p":1,"act":"THIN (overdue)","c":i["c"],"sp":i["sp"],"age":i["age"],
                     "target_sph":i["sph"],"why":f"expected {i['expected']}"})
    for i in f["thin_due"]:
        plan.append({"p":2,"act":"thin","c":i["c"],"sp":i["sp"],"age":i["age"],
                     "target_sph":i["sph"]})
    for i in f["prune_overdue"]:
        plan.append({"p":1,"act":"PRUNE (overdue)","c":i["c"],"sp":i["sp"],"age":i["age"],
                     "to_h_m":i["h"]})
    for i in f["prune_due"]:
        plan.append({"p":2,"act":"prune","c":i["c"],"sp":i["sp"],"age":i["age"],"to_h_m":i["h"]})
    plan.sort(key=lambda x: x["p"])
    return {"total":len(plan),"p1":sum(1 for x in plan if x["p"]==1),
            "shown":min(len(plan),MAX_ACTIONS),"actions":plan[:MAX_ACTIONS]}


# ============================================================
# METRICS TOOLS
# ============================================================

def _stand_metrics(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    code = _norm(a["code"])
    r = db.execute(text("""SELECT compartment_code cc, species sp, age, area_planted ar
        FROM compartments WHERE estate_id=:e AND regexp_replace(regexp_replace(trim(compartment_code),'\\s+','','g'),
            '^([A-Za-z]+)0*([0-9]+)([A-Za-z]?)$','\\1\\2\\3')=:c LIMIT 1"""),
        {"e":eid,"c":code}).mappings().first()
    if not r: return {"found":False,"code":code}
    k = _skey(r["sp"]); age = r["age"]; area = float(r["ar"]) if r["ar"] else 0
    if not k or age is None or not area:
        return {"found":True,"code":code,"note":"Insufficient data."}
    p = SPECIES[k]; mai = p.get("mai",(10,20)); mmid = (mai[0]+mai[1])/2
    rot = p.get("sawlog_yr") or p.get("pole_yr") or (20,25)
    return {"code":r["cc"],"sp":k,"age":age,"ha":area,"mai_mid":mmid,
            "est_volume_m3":round(mmid*age*area),
            "rotation":f"{rot[0]}-{rot[1]}",
            "yrs_to_harvest":f"{max(0,rot[0]-age)}-{max(0,rot[1]-age)}"}

def _explain_compartment(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    code = _norm(a["code"])
    c = _compartment(db, user, {"code":code,"estate_id":eid})
    if not c.get("found"): return c
    hist = _compartment_history(db, user, {"code":code,"estate_id":eid})
    k = _skey(c["sp"])
    p = SPECIES.get(k) if k else None

    ops_done = [o["op"].lower() for o in hist["ops"]]
    missing = []
    if p and c["age"] is not None:
        for w in p.get("weeding", []):
            if c["age"] > w["yr"][1] and "weed" not in " ".join(ops_done):
                missing.append(f"weeding ({w['yr'][0]}-{w['yr'][1]} yr)")
        for pr in p.get("prune", []):
            if c["age"] > pr["yr"][1] and "prune" not in " ".join(ops_done):
                missing.append(f"prune to {pr['h']} m ({pr['yr'][0]}-{pr['yr'][1]} yr)")
        for t in p.get("thin", []):
            if c["age"] > t["yr"][1] and "thin" not in " ".join(ops_done):
                missing.append(f"thin to {t['sph']} sph ({t['yr'][0]}-{t['yr'][1]} yr)")

    return {"compartment":c,"history":hist["ops"],
            "standard":p,"missing":missing}


# ============================================================
# SPATIAL / GIS TOOLS
# ============================================================

def _spatial_in_block(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    blk = (a.get("block") or "").upper()
    rows = db.execute(text("""SELECT compartment_code cc, species sp, age,
        area_planted ar, geom IS NOT NULL AS has_geom
        FROM compartments WHERE estate_id=:e AND UPPER(block_id)=:b
        ORDER BY compartment_code"""),{"e":eid,"b":blk}).mappings().all()
    return {"block":blk,"n":len(rows),"codes":[r["cc"] for r in rows],
            "items":[{"c":r["cc"],"sp":r["sp"],"age":r["age"],
                      "ha":round(float(r["ar"]),1) if r["ar"] else None,
                      "has_geometry":bool(r["has_geom"])} for r in rows]}

def _spatial_neighbours(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    code = _norm(a["code"])
    rows = db.execute(text("""
        WITH target AS (
          SELECT geom FROM compartments
          WHERE estate_id=:e
            AND regexp_replace(regexp_replace(trim(compartment_code),'\\s+','','g'),
                '^([A-Za-z]+)0*([0-9]+)([A-Za-z]?)$','\\1\\2\\3')=:c
          LIMIT 1)
        SELECT c.compartment_code cc, c.species sp, c.age
        FROM compartments c, target t
        WHERE c.estate_id=:e AND c.geom IS NOT NULL AND t.geom IS NOT NULL
          AND ST_Touches(c.geom, t.geom)
        ORDER BY c.compartment_code
    """),{"e":eid,"c":code}).mappings().all()
    return {"code":code,"neighbours":[{"c":r["cc"],"sp":r["sp"],"age":r["age"]}
                                       for r in rows],"n":len(rows)}

def _spatial_near(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    code = _norm(a["code"])
    m = int(a.get("metres") or 500)
    rows = db.execute(text("""
        WITH target AS (
          SELECT geom FROM compartments
          WHERE estate_id=:e
            AND regexp_replace(regexp_replace(trim(compartment_code),'\\s+','','g'),
                '^([A-Za-z]+)0*([0-9]+)([A-Za-z]?)$','\\1\\2\\3')=:c
          LIMIT 1)
        SELECT c.compartment_code cc, c.species sp, c.age,
               ROUND(ST_Distance(c.geom::geography, t.geom::geography)::numeric,1) dist
        FROM compartments c, target t
        WHERE c.estate_id=:e AND c.geom IS NOT NULL AND t.geom IS NOT NULL
          AND ST_DWithin(c.geom::geography, t.geom::geography, :m)
          AND c.compartment_code != :code_raw
        ORDER BY dist ASC LIMIT 20
    """),{"e":eid,"c":code,"m":m,"code_raw":a["code"]}).mappings().all()
    return {"from":code,"metres":m,"n":len(rows),
            "neighbours":[{"c":r["cc"],"sp":r["sp"],"age":r["age"],
                           "dist_m":float(r["dist"])} for r in rows]}

def _spatial_area_summary(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    sql = """SELECT COUNT(*) n, COALESCE(SUM(area_planted),0) ha
             FROM compartments WHERE estate_id=:e"""
    p = {"e":eid}
    if a.get("block"):
        sql += " AND UPPER(block_id)=:b"; p["b"]=a["block"].upper()
    if a.get("species"):
        sql += " AND species ILIKE :sp"; p["sp"]=a["species"]
    if a.get("planting_year"):
        sql += " AND planting_year=:yr"; p["yr"]=int(a["planting_year"])
    r = db.execute(text(sql),p).mappings().first()
    return {"filter":{k:v for k,v in a.items() if k!="estate_id"},
            "compartments":int(r["n"]),"total_area_ha":round(float(r["ha"]),1)}

def _geometry_inventory(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    r = db.execute(text("""SELECT
        COUNT(*) total,
        SUM(CASE WHEN geom IS NOT NULL THEN 1 ELSE 0 END) with_geom,
        MIN(ST_SRID(geom)) srid_min, MAX(ST_SRID(geom)) srid_max
        FROM compartments WHERE estate_id=:e"""),{"e":eid}).mappings().first()
    return {"total_compartments":int(r["total"]),
            "with_geometry":int(r["with_geom"] or 0),
            "without_geometry":int(r["total"])-int(r["with_geom"] or 0),
            "srid_range":f"{r['srid_min']}-{r['srid_max']}" if r["srid_min"] else None}


# ============================================================
# MAP ACTION
# ============================================================

def _map_action(db, user, a):
    codes = a.get("compartment_codes") or []
    return {"action":"highlight",
            "compartment_codes":codes,
            "zoom_to":a.get("zoom_to"),
            "label":a.get("label") or f"{len(codes)} compartments"}


# ============================================================
# REPORTS
# ============================================================

def _generate_estate_report(db, user, a):
    eid = _eid(user, a.get("estate_id"))
    kpi  = _estate_kpis(db, user, {"estate_id":eid})
    spec = _species_breakdown(db, user, {"estate_id":eid})
    ages = _age_distribution(db, user, {"estate_id":eid})
    cov  = _operation_coverage(db, user, {"estate_id":eid})
    gap  = _gap_analysis(db, user, {"estate_id":eid})
    wp   = _work_plan(db, user, {"estate_id":eid})
    return {"kpi":kpi,"species":spec,"age_classes":ages,
            "operation_coverage":cov,"gap_summary":
            {"compartments_with_gaps":gap["compartments_with_gaps"],
             "total":gap["total"]},
            "top_gaps":gap["gaps"],
            "work_plan_summary":{"total":wp["total"],"overdue":wp["p1"]},
            "work_plan_top":wp["actions"][:10]}

def _generate_compartment_report(db, user, a):
    return _explain_compartment(db, user, a)


# ============================================================
# KNOWLEDGE TOOLS
# ============================================================

def _get_species_parameters(db, user, a):
    k = _skey(a.get("species",""))
    if not k:
        return {"found":False,"requested":a.get("species"),"available":list(SPECIES.keys())}
    return {"found":True,"species":k, **SPECIES[k]}

def _get_forestry_standards(db, user, a):
    t = a.get("topic")
    if t and t in REFERENCE: return {"topic":t,"data":REFERENCE[t]}
    return {"topics":list(REFERENCE.keys())}

def _get_zw_regimes(db, user, a):
    return ZW_REGIMES


# ============================================================
# TOOL MAP
# ============================================================

TOOL_MAP = {
    "estate_kpis": _estate_kpis, "find_compartments": _find_compartments,
    "compartment": _compartment, "compartment_history": _compartment_history,
    "list_estates": _list_estates,
    "species_breakdown": _species_breakdown, "block_breakdown": _block_breakdown,
    "age_distribution": _age_distribution, "planting_histogram": _planting_histogram,
    "compare_blocks": _compare_blocks, "operation_coverage": _operation_coverage,
    "find_missing_operations": _find_missing_operations,
    "gap_analysis": _gap_analysis, "assess_status": _assess_status,
    "harvest_ready": _harvest_ready, "work_plan": _work_plan,
    "stand_metrics": _stand_metrics, "explain_compartment": _explain_compartment,
    "spatial_in_block": _spatial_in_block,
    "spatial_neighbours": _spatial_neighbours,
    "spatial_near": _spatial_near,
    "spatial_area_summary": _spatial_area_summary,
    "geometry_inventory": _geometry_inventory,
    "map_action": _map_action,
    "generate_estate_report": _generate_estate_report,
    "generate_compartment_report": _generate_compartment_report,
    "get_species_parameters": _get_species_parameters,
    "get_forestry_standards": _get_forestry_standards,
    "get_zw_regimes": _get_zw_regimes,
}


# ============================================================
# GEMINI SIGNATURE INJECTION (only used for Gemini provider)
# ============================================================

def _inject_gemini_signatures(msgs):
    """Return a shallow copy of msgs with a thought_signature on the
    first tool_call of every assistant message that has tool_calls.
    Only Gemini 3.x requires this."""
    out = []
    for m in msgs:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            new_m = dict(m)
            new_tcs = []
            for idx, tc in enumerate(m["tool_calls"]):
                tc_copy = dict(tc)
                if idx == 0:
                    tc_copy["extra_content"] = {
                        "google": {
                            "thought_signature": "skip_thought_signature_validator"
                        }
                    }
                new_tcs.append(tc_copy)
            new_m["tool_calls"] = new_tcs
            out.append(new_m)
        else:
            out.append(m)
    return out


# ============================================================
# FALLBACK-AWARE API CALLER
# ============================================================

def _call_with_fallback(msgs, max_retries_per_provider=1):
    """Try each provider. On 429, wait with exponential backoff +
    jitter before trying the next provider."""
    last_exc = None
    _rate_limited = set()

    for prov in _clients:
        if prov["name"] in _rate_limited:
            continue

        for attempt in range(max_retries_per_provider):
            try:
                print(f"[chatbot] Trying {prov['name']} "
                      f"(attempt {attempt+1}/{max_retries_per_provider})")

                # Gemini needs thought_signature on tool_calls.
                # Mistral / Groq / Cerebras / SambaNova reject extra fields.
                if prov["name"] == "Gemini":
                    send_msgs = _inject_gemini_signatures(msgs)
                else:
                    send_msgs = msgs

                kwargs = dict(
                    model=prov["model"],
                    messages=send_msgs,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=700,
                )
                return prov["client"].chat.completions.create(**kwargs)
            except Exception as e:
                s = str(e)
                last_exc = e

                if "429" not in s and "rate_limit" not in s.lower():
                    print(f"[chatbot] {prov['name']} error: {s[:150]}")
                    break

                _rate_limited.add(prov["name"])
                if attempt < max_retries_per_provider - 1:
                    base = 2 ** attempt
                    wait = base + random.uniform(0, base)
                    print(f"[chatbot] {prov['name']} 429, wait {wait:.1f}s")
                    time.sleep(wait)
                else:
                    print(f"[chatbot] {prov['name']} exhausted")

    raise last_exc or RuntimeError("All AI providers rate-limited")


# ============================================================
# ENTRY POINT
# ============================================================

def ask_assistant(message, history, user, db):
    if not _clients:
        return {"reply": "The AI assistant is not configured.", "map_action": None}

    msgs = [{"role": "system", "content": SYSTEM_PROMPT.format(
        role=user["role"], estate=user.get("estate_id") or "all")}]

    for t in (history or [])[-1:]:
        if t.get("role") in ("user", "assistant") and t.get("content"):
            msgs.append({"role": t["role"], "content": str(t["content"])[:300]})
    msgs.append({"role": "user", "content": message})

    map_action = None

    try:
        for _ in range(3):
            r = _call_with_fallback(msgs)
            m = r.choices[0].message

            if not m.tool_calls:
                reply = m.content
                if reply is None:
                    reply = "(no answer)"
                elif not isinstance(reply, str):
                    reply = str(reply)
                return {"reply": reply, "map_action": map_action}

            # Build plain tool_calls. Gemini's signature is injected
            # only when we're about to call Gemini (see _call_with_fallback).
            tool_calls_payload = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in m.tool_calls
            ]

            msgs.append({
                "role": "assistant",
                "content": m.content,
                "tool_calls": tool_calls_payload,
            })

            for tc in m.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                fn = TOOL_MAP.get(name)
                if fn is None:
                    res = {"error": f"unknown tool {name}"}
                else:
                    try:
                        res = fn(db, user, args)
                    except Exception as e:
                        res = {"error": str(e)}

                if name == "map_action" and isinstance(res, dict):
                    map_action = res

                msgs.append({
                    "role": "tool", "tool_call_id": tc.id,
                    "content": json.dumps(res, default=str,
                                          separators=(",", ":")),
                })

        return {"reply": "The assistant couldn't complete that request.",
                "map_action": map_action}

    except Exception as e:
        return {"reply": f"AI error: {type(e).__name__}: {str(e)[:300]}",
                "map_action": None}