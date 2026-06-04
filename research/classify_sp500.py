#!/usr/bin/env python3
"""
Classify S&P 500 companies by main product, enabling technology, and underlying science.
Uses hardcoded expert knowledge for tech/science-driven companies.

Usage:
  python research/classify_sp500.py
"""

import csv
import sys

INPUT = "/home/ubuntu/trend-digest/data/sp500.csv"
OUTPUT = "/home/ubuntu/trend-digest/data/sp500_classified.csv"

# ticker -> (main_product, enabling_tech, underlying_science)
CLASSIFICATIONS = {
    # === SEMICONDUCTORS + CHIP DESIGN ===
    "NVDA": ("AI/ML accelerators + GPUs", "massively parallel GPU computing", "deep learning + linear algebra"),
    "AMD":  ("CPUs + GPUs + AI chips", "chip microarchitecture design", "semiconductor physics + computer architecture"),
    "AVGO": ("networking + storage + AI ASICs", "custom ASIC design", "semiconductor physics"),
    "QCOM": ("mobile SoCs + 5G modems", "CDMA/5G wireless + RF integration", "signal processing + electromagnetic theory"),
    "TXN":  ("analog + embedded semiconductors", "analog circuit design", "semiconductor physics + circuit theory"),
    "INTC": ("CPUs + data center chips", "x86 architecture + process node shrink", "semiconductor physics"),
    "MU":   ("DRAM + NAND flash memory", "flash memory cell design", "semiconductor physics + charge trapping"),
    "MRVL": ("data center + networking chips", "SerDes + DSP for high-speed links", "signal processing + semiconductor physics"),
    "MCHP": ("microcontrollers + FPGAs", "embedded processor design", "semiconductor physics"),
    "ON":   ("power + automotive semiconductors", "SiC MOSFET + power electronics", "semiconductor physics + wide-bandgap materials"),
    "STX":  ("hard disk drives", "perpendicular magnetic recording", "physics of magnetic media"),
    "WDC":  ("hard drives + NAND flash", "magnetic recording + flash memory", "semiconductor physics"),
    "SWKS": ("RF analog semiconductors", "RF front-end modules", "RF engineering + semiconductor physics"),
    "AMAT": ("semiconductor fab equipment", "CVD/PVD thin-film deposition + etch", "materials science + plasma physics"),
    "LRCX": ("semiconductor etch equipment", "plasma etching", "plasma physics + materials science"),
    "KLAC": ("semiconductor process control", "optical + e-beam metrology", "optics + signal processing"),
    "TER":  ("semiconductor test equipment", "automated test equipment", "electrical engineering"),
    "SNPS": ("EDA software", "chip design automation + formal verification", "algorithms + Boolean logic"),
    "CDNS": ("EDA + IP for chip design", "circuit simulation + place-and-route", "algorithms + circuit theory"),

    # === CLOUD + SOFTWARE PLATFORMS ===
    "MSFT": ("cloud (Azure) + AI + enterprise software", "cloud computing + large language models", "distributed systems + machine learning"),
    "GOOGL":("search + cloud + AI", "PageRank + transformer LLMs", "information retrieval + deep learning"),
    "GOOG": ("search + cloud + AI", "PageRank + transformer LLMs", "information retrieval + deep learning"),
    "META": ("social media + VR/AR + AI", "social graph algorithms + LLMs + computer vision", "graph theory + deep learning"),
    "CRM":  ("cloud CRM + AI agents", "SaaS + vector search + LLMs", "machine learning"),
    "ORCL": ("cloud database + ERP", "relational databases + cloud infrastructure", "database theory"),
    "SAP":  ("enterprise ERP + cloud", "ERP software", "none"),
    "ADBE": ("creative software + generative AI", "generative AI + image/video processing", "computer vision + diffusion models"),
    "NOW":  ("cloud workflow automation", "SaaS platform + AI", "none"),
    "INTU": ("financial software + AI", "ML for tax + accounting", "machine learning"),
    "PANW": ("cybersecurity platform", "AI-based threat detection + XDR", "machine learning"),
    "CRWD": ("cloud-native endpoint security", "behavioral AI for threat detection", "machine learning"),
    "FTNT": ("network security", "ASIC-accelerated firewall + SD-WAN", "network security"),
    "ZS":   ("cloud security + zero trust", "zero trust network access", "network security"),
    "ANSS": ("simulation software", "finite element analysis + CFD", "computational physics + numerical methods"),

    # === HARDWARE + DEVICES ===
    "AAPL": ("iPhone + Mac + services", "custom silicon (Apple Silicon) + mobile OS", "semiconductor physics + computer architecture"),
    "ISRG": ("robotic surgery systems", "robotic-assisted minimally invasive surgery", "robotics + computer vision + haptics"),
    "HPE":  ("enterprise servers + networking", "server + HPC architecture", "computer architecture"),
    "NTAP": ("cloud data storage management", "storage software + flash arrays", "none"),

    # === PHARMA + BIOTECH ===
    "LLY":  ("GLP-1 drugs (Ozempic/Mounjaro) + Alzheimer drug", "peptide + small molecule drug design", "GLP-1 receptor biology + amyloid biology"),
    "JNJ":  ("pharmaceuticals + medical devices", "biologics + surgical robotics", "immunology + bioengineering"),
    "MRK":  ("cancer immunotherapy (Keytruda) + vaccines", "PD-1 checkpoint inhibitor + mRNA vaccines", "immuno-oncology + mRNA biology"),
    "ABBV": ("immunology drugs (Humira/Rinvoq)", "JAK inhibitors + monoclonal antibodies", "immunology + protein engineering"),
    "BMY":  ("oncology + cardiovascular drugs", "PD-1 checkpoint inhibitors + small molecules", "immuno-oncology + medicinal chemistry"),
    "AMGN": ("biologics (Enbrel, Repatha)", "monoclonal antibodies + biosimilars", "protein engineering + immunology"),
    "GILD": ("antiviral drugs (HIV, COVID)", "nucleotide analog antivirals", "virology + medicinal chemistry"),
    "REGN": ("antibody drugs (Dupixent, Eylea)", "fully human antibody platform (VelocImmune)", "immunology + genetics"),
    "VRTX": ("cystic fibrosis + pain drugs", "CFTR modulators + sodium channel blockers", "molecular biology + ion channel biophysics"),
    "BIIB": ("neurology drugs (MS, Alzheimer)", "antisense oligonucleotides + antibodies", "neuroscience + molecular biology"),
    "MRNA": ("mRNA vaccines + therapeutics", "lipid nanoparticle mRNA delivery", "mRNA biology + lipid chemistry"),
    "ALNY": ("RNAi therapeutics", "RNA interference + GalNAc delivery", "RNA biology + gene silencing"),
    "ILMN": ("DNA sequencing instruments", "sequencing-by-synthesis (SBS)", "genomics + biochemistry + optics"),
    "EW":   ("transcatheter heart valves + hemodynamics", "transcatheter valve delivery", "bioengineering + fluid dynamics"),
    "BSX":  ("cardiac + endoscopy devices", "interventional cardiology devices", "materials science + bioengineering"),
    "ZBH":  ("orthopedic implants + robotics", "3D-printed implants + surgical robots", "materials science + robotics"),
    "STE":  ("sterilization + infection prevention", "ethylene oxide + H2O2 sterilization", "microbiology + chemistry"),
    "HOLX": ("women's health diagnostics + imaging", "PCR-based diagnostics + digital mammography", "molecular biology + X-ray imaging"),
    "BIO":  ("life science research tools", "recombinant proteins + flow cytometry", "molecular biology"),
    "A":    ("analytical instruments + diagnostics", "LC-MS + genomics instruments", "analytical chemistry + mass spectrometry"),
    "TMO":  ("lab instruments + biotech manufacturing", "mass spectrometry + sequencing + bioreactors", "analytical chemistry + biochemistry"),
    "DHR":  ("life science + diagnostics instruments", "chromatography + mass spec + sequencing", "analytical chemistry + molecular biology"),
    "IQV":  ("clinical research + data services", "real-world data analytics + AI for trials", "statistics + machine learning"),
    "IDXX": ("veterinary diagnostics", "PCR + rapid immunoassay diagnostics", "molecular biology + immunology"),
    "MTD":  ("precision instruments + lab balances", "precision measurement + automation", "metrology + analytical chemistry"),
    "WAT":  ("analytical instruments (HPLC, MS)", "liquid chromatography + mass spectrometry", "analytical chemistry"),
    "PKI":  ("diagnostics + life science tools", "immunoassay + molecular diagnostics", "immunology + molecular biology"),
    "BAX":  ("renal + hospital products", "hemodialysis technology", "bioengineering + membrane science"),
    "BDX":  ("medical devices + diagnostics", "flow cytometry + microbiology diagnostics", "molecular biology + optics"),
    "SYK":  ("surgical robots + orthopedics + neurotechnology", "Mako robotic surgery system", "robotics + materials science"),
    "MDT":  ("cardiac devices + neuromodulation", "pacemakers + deep brain stimulation", "bioelectronics + neuroscience"),
    "ABT":  ("diagnostics + medical devices", "immunoassay + continuous glucose monitoring", "electrochemistry + immunology"),
    "ABBV": ("immunology + oncology biologics", "monoclonal antibodies + ADCs", "protein engineering + immunology"),

    # === LIFE SCIENCE TOOLS ===
    "TECH": ("cytokines + proteins for research", "recombinant protein expression", "protein biology"),
    "MASI": ("pulse oximetry + patient monitoring", "optical blood oxygen sensing", "spectroscopy + physiology"),
    "ALGN": ("clear dental aligners", "3D imaging + custom polymer fabrication", "materials science + computer vision"),

    # === ENERGY TECH ===
    "ENPH": ("solar microinverters + energy management", "power electronics + IoT for solar", "electrical engineering"),
    "FSLR": ("thin-film solar panels", "cadmium telluride (CdTe) photovoltaics", "semiconductor physics + thin-film deposition"),
    "NEE":  ("wind + solar power generation", "utility-scale renewable energy", "electrical engineering"),
    "CEG":  ("nuclear + renewable power", "nuclear fission power generation", "nuclear physics"),
    "D":    ("natural gas + nuclear utilities", "nuclear + gas generation", "nuclear physics"),
    "PCG":  ("electric + gas utility", "grid infrastructure", "electrical engineering"),

    # === MATERIALS + CHEMICALS (science-driven) ===
    "ALB":  ("lithium compounds for batteries", "lithium carbonate + lithium hydroxide refining", "electrochemistry + materials science"),
    "APD":  ("industrial gases (H2, O2, N2)", "cryogenic gas separation + green hydrogen", "chemical engineering + thermodynamics"),
    "IFF":  ("flavors + fragrances + ingredients", "synthetic biology for flavor molecules", "biochemistry + synthetic biology"),
    "PPG":  ("coatings + paints", "polymer chemistry + nano-coatings", "polymer chemistry + materials science"),
    "LIN":  ("industrial + medical gases + hydrogen", "air separation + hydrogen electrolysis", "chemical engineering + electrochemistry"),
    "SHW":  ("paints + coatings", "polymer chemistry", "polymer chemistry"),
    "DD":   ("specialty materials + chemicals", "polymer science + materials engineering", "polymer chemistry + materials science"),
    "DOW":  ("commodity + specialty chemicals", "polyethylene + silicones", "polymer chemistry"),
    "LYB":  ("polyolefins + chemicals", "polyolefin catalysis", "polymer chemistry + catalysis"),
    "EMN":  ("specialty chemicals + materials", "polymer + fiber technology", "polymer chemistry"),
    "FMC":  ("crop protection chemicals", "synthetic pesticide chemistry", "agrochemistry"),
    "CF":   ("nitrogen fertilizers", "Haber-Bosch ammonia synthesis", "industrial chemistry"),
    "MOS":  ("phosphate + potash fertilizers", "mineral extraction + processing", "geology + chemistry"),

    # === AUTOMOTIVE + ELECTRIFICATION ===
    "TSLA": ("electric vehicles + energy storage + AI autonomy", "lithium-ion batteries + FSD neural nets + power electronics", "electrochemistry + deep learning + power electronics"),
    "F":    ("ICE + EV vehicles", "electric motor + battery integration", "mechanical engineering + electrochemistry"),
    "GM":   ("ICE + EV vehicles (Ultium platform)", "Ultium battery platform + ADAS", "electrochemistry + machine learning"),
    "APTV": ("vehicle electronics + software", "ADAS + EV wiring architecture", "embedded systems + computer vision"),

    # === AEROSPACE + DEFENSE ===
    "BA":   ("commercial aircraft + defense", "composite airframes + turbofan engines", "aerospace engineering + materials science"),
    "RTX":  ("jet engines (Pratt & Whitney) + missiles + avionics (Raytheon)", "gas turbine + AESA radar + precision guidance", "thermodynamics + RF engineering + inertial navigation"),
    "LMT":  ("fighter jets + missiles + space systems", "stealth materials + hypersonics + AESA radar", "RF-absorbing materials + aerodynamics + RF engineering"),
    "NOC":  ("B-21 bomber + space + cyber", "low-observable (stealth) + space sensors", "RF engineering + aerodynamics"),
    "GD":   ("nuclear submarines + tanks + Gulfstream jets", "nuclear propulsion + advanced composites", "nuclear engineering + materials science"),
    "HII":  ("nuclear-powered aircraft carriers + submarines", "naval nuclear propulsion", "nuclear engineering"),
    "TDG":  ("aerospace components", "high-tolerance aerospace manufacturing", "materials science + aerospace engineering"),
    "HWM":  ("aerospace components (turbine blades)", "single-crystal superalloy turbine blades", "materials science + metallurgy"),

    # === INDUSTRIAL AUTOMATION + ROBOTICS ===
    "ROK":  ("industrial automation + IoT", "PLC + industrial software + AI for manufacturing", "control systems + machine learning"),
    "EMR":  ("industrial automation + HVAC controls", "process control + smart sensors", "control systems engineering"),
    "HON":  ("aerospace avionics + building controls + safety", "sensor fusion + IoT for buildings + avionics", "electronics + aerospace engineering"),
    "ETN":  ("electrical power management", "power electronics + grid components", "electrical engineering"),
    "ITW":  ("industrial equipment + fasteners", "manufacturing process technology", "mechanical engineering"),
    "PH":   ("motion + control systems (hydraulics, pneumatics)", "fluid power + motion control", "fluid mechanics + control systems"),
    "IR":   ("climate + industrial solutions", "HVAC compressor + refrigerant systems", "thermodynamics + refrigeration"),
    "CARR": ("HVAC + refrigeration", "vapor-compression refrigeration", "thermodynamics"),
    "TT":   ("HVAC systems", "vapor-compression + heat pump systems", "thermodynamics"),
    "OTIS": ("elevators + escalators", "linear motor + safety systems", "mechanical engineering + control systems"),
    "AME":  ("electronic instruments + electromechanical", "precision sensors + power quality", "electronics + metrology"),

    # === COMMUNICATION INFRASTRUCTURE ===
    "AMT":  ("cell towers + wireless infrastructure", "RF antenna + tower engineering", "RF engineering + electromagnetics"),
    "CCI":  ("cell towers + small cells + fiber", "wireless network densification", "RF engineering"),
    "SBAC": ("cell towers", "wireless infrastructure", "RF engineering"),
    "VZ":   ("5G wireless + broadband", "5G NR (New Radio) networks", "signal processing + RF engineering"),
    "T":    ("5G wireless + fiber broadband", "5G + fiber-to-the-home", "signal processing + RF engineering"),

    # === AI-DRIVEN DATA / CLOUD ===
    "PLTR": ("AI analytics for defense + enterprise", "LLM-based data fusion + ontology graphs", "machine learning + graph theory"),
    "SNOW": ("cloud data warehouse", "columnar storage + query optimization", "database theory + distributed systems"),
    "MDB":  ("document database (MongoDB)", "NoSQL document store + Atlas cloud", "distributed systems + database theory"),
    "NET":  ("cloud network + security (Cloudflare)", "anycast CDN + edge compute + zero trust", "network engineering + distributed systems"),
    "DDOG": ("cloud monitoring + observability", "time-series data + ML anomaly detection", "machine learning + distributed systems"),
    "WDAY": ("cloud HR + finance software", "SaaS platform", "none"),
    "VEEV": ("cloud software for life sciences", "regulatory data management", "none"),

    # === SPACE + SATELLITES ===
    "TDG":  ("aerospace components", "precision aerospace manufacturing", "materials science + aerospace engineering"),
    "SPGI": ("financial data + analytics", "data analytics + AI", "none"),  # S&P Global, not space

    # === CLEAN TECH / GRID ===
    "BKR":  ("oilfield services + industrial tech", "subsurface sensing + LNG tech", "geophysics + thermodynamics"),
    "SLB":  ("oilfield services + digital for energy", "seismic imaging + AI for reservoir modeling", "geophysics + machine learning"),
    "HAL":  ("oilfield services", "drilling + completion technology", "mechanical + petroleum engineering"),
}

NONE = ("none", "none", "none")


def main():
    with open(INPUT) as f:
        companies = list(csv.DictReader(f))
    print(f"Loaded {len(companies)} companies", file=sys.stderr)

    fieldnames = ["ticker", "name", "sector", "industry", "main_product", "enabling_tech", "underlying_science"]
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in companies:
            mp, et, us = CLASSIFICATIONS.get(c["ticker"], NONE)
            writer.writerow({
                "ticker": c["ticker"],
                "name": c["name"],
                "sector": c["sector"],
                "industry": c["industry"],
                "main_product": mp,
                "enabling_tech": et,
                "underlying_science": us,
            })

    tech_count = sum(1 for c in companies if CLASSIFICATIONS.get(c["ticker"], NONE)[1] != "none")
    print(f"Wrote {len(companies)} rows ({tech_count} tech/science-driven) to {OUTPUT}", file=sys.stderr)

    # Print summary
    print("\nTech/science-driven companies:", file=sys.stderr)
    for c in companies:
        mp, et, us = CLASSIFICATIONS.get(c["ticker"], NONE)
        if et != "none":
            print(f"  {c['ticker']:6} {c['name'][:38]:38} | {et[:38]:38} | {us}", file=sys.stderr)


if __name__ == "__main__":
    main()
