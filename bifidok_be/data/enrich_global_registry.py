import json
import os

OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "global_enterprise_universe.py")

ADDITIONAL_GLOBAL_REGISTRY = [
    # US Tech Giants
    ("Apple Inc.", "apple.com", "US", "Consumer Electronics & Cloud Services", 161000, 0.303, True, ["iOS Platform Lead", "Swift Infrastructure Architect", "Privacy & Security Engineer"], True, True, True, "A", [], 0, 1200, 0.93, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.91, "Private Cloud Compute deployment and Swift generative framework."),
    ("Meta Platforms, Inc.", "meta.com", "US", "Social Media & Open-Source AI Infrastructure", 67317, 0.400, True, ["Llama Infrastructure Lead", "PyTorch Core Developer", "Datacenter Systems Engineer"], True, True, True, "A", [], 0, 2500, 0.95, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.94, "Llama open-source foundation model scaling and custom silicon deployments."),
    ("Tesla, Inc.", "tesla.com", "US", "Automotive & Energy Storage", 140473, 0.082, True, ["FSD Neural Network Engineer", "Dojo Systems Architect", "Factory Automation Specialist"], True, True, True, "A", [], 0, 310, 0.94, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.92, "Dojo supercomputing cluster scaling and humanoid robotics factory automation."),
    ("Adobe Inc.", "adobe.com", "US", "Creative & Document Cloud Software", 29945, 0.355, True, ["Firefly AI Architect", "Cloud Reliability Engineer", "Enterprise Platform Lead"], True, True, True, "A", [], 0, 450, 0.92, 0.0, 1.0, 2, 4.5, 1.0, 0.0, 0.88, "Firefly generative AI integrations across Fortune 500 creative workflows."),
    ("Advanced Micro Devices (AMD)", "amd.com", "US", "Semiconductors & Accelerators", 26000, 0.155, True, ["ROCm Software Engineer", "MI300 Platform Architect", "HPC Cloud Specialist"], True, True, True, "A", [], 0, 520, 0.92, 0.0, 1.0, 2, 4.5, 1.0, 0.0, 0.90, "MI300X AI accelerator deployments and ROCm open software stack expansions."),
    ("Intel Corporation", "intel.com", "US", "Semiconductor Manufacturing & Architecture", 124800, 0.035, True, ["Foundry Automation Engineer", "Silicon Architect", "Cybersecurity Lead"], True, True, True, "B", ["CSP"], 1, 980, 0.89, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.82, "Intel Foundry IFS manufacturing transition and enterprise server CPU roadmaps."),
    ("Qualcomm Incorporated", "qualcomm.com", "US", "Wireless Technologies & Mobile SoC", 50000, 0.285, True, ["Oryon CPU Architect", "Edge AI Software Engineer", "Automotive Platform Lead"], True, True, True, "A", [], 0, 380, 0.91, 0.0, 1.0, 2, 4.5, 1.0, 0.0, 0.87, "Snapdragon X Elite on-device Copilot+ PC silicon and automotive cockpit compute."),
    ("Uber Technologies, Inc.", "uber.com", "US", "Mobility & Delivery Platform", 32800, 0.085, True, ["Fleet Routing Lead", "Marketplace Algorithms Architect", "Cloud Platform Engineer"], True, True, True, "A", [], 0, 680, 0.95, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.92, "Dynamic marketplace routing overhaul and global delivery automation."),
    ("Netflix, Inc.", "netflix.com", "US", "Streaming Entertainment & Content Delivery", 13000, 0.238, True, ["Open Connect CDN Architect", "Streaming Systems Lead", "Machine Learning SRE"], True, False, True, "A", [], 0, 420, 0.90, 0.0, 1.0, 2, 4.0, 1.0, 0.0, 0.88, "Global Open Connect edge caching and cloud recommendation microservices."),
    ("Intuit Inc.", "intuit.com", "US", "Financial & Tax Software Platforms", 18200, 0.235, True, ["GenOS AI Platform Architect", "FinTech Security Specialist", "Cloud Systems Engineer"], True, True, True, "A", [], 0, 310, 0.93, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.89, "Intuit GenOS agentic tax assistant rollouts for TurboTax and QuickBooks."),
    ("Workday, Inc.", "workday.com", "US", "Cloud Human Capital & ERP Management", 18800, 0.165, True, ["Illuminated AI Architect", "HCM Cloud Specialist", "Security Compliance Officer"], True, True, True, "A", [], 0, 240, 0.94, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.90, "Workday Illuminate AI intelligence platform integration into core HCM workflows."),
    ("Palantir Technologies", "palantir.com", "US", "Enterprise Big Data & Defense Software", 3800, 0.185, True, ["AIP Deployment Strategist", "Ontology Engineer", "Forward Deployed Software Engineer"], True, True, True, "A", [], 0, 190, 0.96, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.94, "AIP bootcamps driving commercial contract acceleration across US enterprises."),
    ("MongoDB, Inc.", "mongodb.com", "US", "Developer Data Platform & NoSQL", 5000, 0.075, True, ["Atlas Vector Search Engineer", "Distributed Database Architect", "Cloud Security Lead"], True, False, True, "A", [], 0, 480, 0.92, 0.0, 1.0, 2, 4.0, 1.0, 0.0, 0.89, "MongoDB Atlas vector search expansion for enterprise GenAI applications."),
    ("Twilio Inc.", "twilio.com", "US", "Customer Engagement Platform & Communications", 5800, 0.065, True, ["Segment CDP Architect", "Communications API Specialist", "InfoSec Lead"], True, True, True, "A", [], 0, 340, 0.91, 0.0, 1.0, 0, 4.0, 1.0, 1.0, 0.86, "Twilio CustomerAI embedding predictive and generative insights into Segment."),
    ("Arista Networks", "arista.com", "US", "Cloud Networking Solutions", 4200, 0.420, True, ["EOS Software Engineer", "AI Spine Network Architect", "Zero Trust Engineer"], True, True, True, "A", [], 0, 150, 0.93, 0.0, 1.0, 2, 4.5, 1.0, 0.0, 0.91, "Ultra Ethernet Consortium high-throughput backbones for AI GPU clusters."),

    # US Financials
    ("Visa Inc.", "visa.com", "US", "Global Payments Technology", 28800, 0.672, True, ["VisaNet Architect", "Fraud Detection AI Specialist", "Cyber Defense Lead"], True, True, True, "A", [], 0, 110, 0.94, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.92, "VisaNet infrastructure resilience and real-time AI payment dispute automation."),
    ("Mastercard Incorporated", "mastercard.com", "US", "Payment Network & Cyber Intelligence", 33400, 0.585, True, ["Cyber & Intelligence Lead", "Open Banking Architect", "Threat Intel Analyst"], True, True, True, "A", [], 0, 140, 0.94, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.91, "Cyber & Intelligence solutions expansion protecting digital transaction gateways."),
    ("American Express Company", "americanexpress.com", "US", "Payments & Travel Services", 74600, 0.225, True, ["Fraud Platform Engineer", "Cloud Security Architect", "Risk Analytics Lead"], True, True, True, "A", [], 0, 95, 0.92, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.89, "Enterprise hybrid cloud migration and transaction security automation."),
    ("Goldman Sachs Group", "goldmansachs.com", "US", "Investment Banking & Wealth Management", 45300, 0.265, True, ["Quantitative SRE", "Marquee Platform Lead", "InfoSec Red Team Lead"], True, True, True, "A", [], 0, 120, 0.91, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.90, "Financial cloud platformization with AWS and regulatory reporting automation."),
    ("Morgan Stanley", "morganstanley.com", "US", "Wealth Management & Institutional Securities", 82000, 0.252, True, ["Wealth Management AI Lead", "Cloud Infrastructure Architect", "Cyber Compliance Officer"], True, True, True, "A", [], 0, 85, 0.91, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.89, "Deployment of OpenAI-powered assistant for financial advisors."),
    ("Citigroup Inc.", "citigroup.com", "US", "Global Diversified Financial Services", 239000, 0.185, True, ["Transformation Risk Officer", "Cloud Modernization Architect", "SOC Analyst"], True, True, True, "B", ["CSP"], 1, 110, 0.89, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.86, "Multi-year regulatory data architecture transformation and core consolidation."),
    ("BlackRock, Inc.", "blackrock.com", "US", "Investment Management & Aladdin Platform", 19800, 0.365, True, ["Aladdin Systems Architect", "Data Platform Engineer", "Cyber Defense Specialist"], True, True, True, "A", [], 0, 160, 0.94, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.91, "Aladdin multi-asset risk operating system expansion across institutional asset managers."),

    # US Retail & Consumer
    ("Costco Wholesale Corporation", "costco.com", "US", "Membership Warehouse Retail", 316000, 0.038, True, ["Warehouse Systems Engineer", "Supply Chain Analyst", "IT Modernization Lead"], True, True, True, "B", ["CSP"], 0, 35, 0.90, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.85, "Supply chain optical sorting and inventory tracking system overhaul."),
    ("The Home Depot, Inc.", "homedepot.com", "US", "Home Improvement Retail & Supply Chain", 465000, 0.142, True, ["Supply Chain Automation Architect", "Omnichannel Lead", "Cyber Defense Specialist"], True, True, True, "A", [], 0, 65, 0.92, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.88, "Supply chain flatbed distribution center automation and omnichannel fulfillment."),
    ("Target Corporation", "target.com", "US", "General Merchandise Retail", 415000, 0.053, True, ["Sortation Robotics Lead", "Cloud Reliability Engineer", "Retail Security Analyst"], True, True, True, "B", ["CSP"], 0, 70, 0.91, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.86, "Store-as-hub sorting automation and last-mile sortation hub expansions."),
    ("Starbucks Corporation", "starbucks.com", "US", "Specialty Coffee Retail & Mobile Commerce", 381000, 0.150, True, ["Deep Brew AI Specialist", "Store Systems Architect", "Supply Chain Lead"], True, True, True, "A", [], 0, 45, 0.90, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.87, "Deep Brew machine learning engine automating inventory ordering across retail stores."),
    ("McDonald's Corporation", "mcdonalds.com", "US", "Global Restaurant Franchising & Technology", 150000, 0.465, True, ["Digital Customer Architect", "Kitchen Automation Lead", "Cloud Security Engineer"], True, True, True, "A", [], 0, 50, 0.91, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.88, "Google Cloud strategic partnership deploying edge computing across global restaurants."),
    ("Nike, Inc.", "nike.com", "US", "Athletic Footwear & Apparel", 83700, 0.118, True, ["Direct-to-Consumer Cloud Architect", "Supply Chain Analytics Lead", "InfoSec Engineer"], True, True, True, "A", [], 0, 80, 0.91, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.88, "Enterprise ERP harmonization and direct-to-consumer digital supply chain."),

    # US Aerospace, Defense & Industrial
    ("Lockheed Martin Corporation", "lockheedmartin.com", "US", "Aerospace, Defense & Advanced Technology", 122000, 0.128, True, ["1LMX Digital Transformation Lead", "CMMC Level 3 Cyber Auditor", "Zero Trust Architect"], True, True, True, "A", [], 0, 65, 0.93, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.92, "1LMX digital transformation replacing legacy manufacturing with cloud architectures."),
    ("RTX Corporation (Raytheon)", "rtx.com", "US", "Aerospace & Defense Systems", 185000, 0.098, True, ["Avionics Cloud Lead", "Defense Cyber Architect", "Manufacturing Automation Engineer"], True, True, True, "A", [], 0, 55, 0.92, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.90, "Digital factory modernization and DoD secure cloud collaboration environment."),
    ("Caterpillar Inc.", "caterpillar.com", "US", "Construction & Mining Equipment", 113200, 0.205, True, ["Autonomous Haulage Systems Lead", "Connected Fleet Architect", "Cybersecurity Engineer"], True, True, True, "A", [], 0, 50, 0.92, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.89, "Cat Command autonomous mining haulage systems and IoT fleet telematics."),
    ("Deere & Company (John Deere)", "deere.com", "US", "Precision Agriculture & Heavy Machinery", 83000, 0.215, True, ["See & Spray AI Engineer", "Precision Ag Cloud Architect", "Embedded Cyber Lead"], True, True, True, "A", [], 0, 90, 0.93, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.90, "See & Spray computer vision robotics and autonomous tractor software platforms."),
    ("Honeywell International", "honeywell.com", "US", "Aerospace & Industrial Automation Controls", 95000, 0.198, True, ["Forge IoT Platform Architect", "OT Cyber Specialist", "Cloud Operations Lead"], True, True, True, "A", [], 0, 75, 0.92, 0.0, 1.0, 1, 5.0, 1.0, 1.0, 0.89, "Honeywell Forge IoT platform driving OT industrial cybersecurity defense."),

    # European Leaders
    ("Airbus SE", "airbus.com", "FR", "Commercial Aircraft & Aerospace", 147982, 0.075, True, ["Skywise Cloud Architect", "Cybersecurity Incident Officer", "Manufacturing IT Lead"], True, True, True, "A", [], 0, 110, 0.94, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.91, "Skywise aviation data platform and sovereign EU defense cloud modernization."),
    ("BMW Group", "bmw.com", "DE", "Automotive & Premium Mobility", 154950, 0.110, True, ["Autonomous Driving Systems Engineer", "Connected Car Cloud Lead", "Factory AI Specialist"], True, True, True, "A", [], 0, 160, 0.93, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.90, "iFactory digital production rollout using NVIDIA Omniverse digital twins."),
    ("Mercedes-Benz Group AG", "mercedes-benz.com", "DE", "Luxury Vehicles & Automotive", 166056, 0.126, True, ["MB.OS Software Architect", "Vehicle Cyber Security Engineer", "Cloud Operations Specialist"], True, True, True, "A", [], 0, 140, 0.93, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.90, "MB.OS proprietary operating system rollout with automated OTA updates."),
    ("Volkswagen Group", "volkswagen.de", "DE", "Automotive Conglomerate & EV Systems", 684000, 0.070, True, ["CARIAD Platform Architect", "Battery Gigafactory IT Lead", "Production Automation Engineer"], True, True, True, "B", ["CSP"], 1, 210, 0.91, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.88, "CARIAD software architecture consolidation and PowerCo battery factory IT."),
    ("LVMH Moet Hennessy Louis Vuitton", "lvmh.com", "FR", "Luxury Goods & Retail", 213000, 0.260, True, ["Clienteling Cloud Architect", "Omnichannel Systems Lead", "Supply Chain Integrity Officer"], True, True, True, "A", [], 0, 45, 0.91, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.88, "AI-driven luxury clienteling and blockchain product authenticity tracking."),
    ("L'Oreal S.A.", "loreal.com", "FR", "Cosmetics & Beauty Tech", 90000, 0.198, True, ["Beauty Tech Platform Lead", "Supply Chain Automation Engineer", "Consumer Cyber Officer"], True, True, True, "A", [], 0, 55, 0.90, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.87, "Global Beauty Tech transformation and digital consumer experience personalization."),
    ("Nestle S.A.", "nestle.com", "CH", "Food & Beverage Conglomerate", 270000, 0.173, True, ["Supply Chain Digital Lead", "Global ERP Cloud Architect", "Cyber Compliance Lead"], True, True, True, "A", [], 0, 60, 0.91, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.88, "Global supply chain visibility and automated demand forecasting modernization."),
    ("Novartis AG", "novartis.com", "CH", "Innovative Medicines & Healthcare", 76000, 0.285, True, ["Biomedical Cloud Architect", "GxP Quality Systems Lead", "Cyber Defense Specialist"], True, True, True, "A", [], 0, 85, 0.92, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.89, "AI-powered clinical trial optimization and Microsoft Azure scientific cloud."),
    ("Roche Holding AG", "roche.com", "CH", "Pharmaceuticals & Diagnostics", 103600, 0.292, True, ["Diagnostic Cloud Platform Lead", "Genomics Data Architect", "InfoSec Auditor"], True, True, True, "A", [], 0, 90, 0.93, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.90, "NAVIFY digital diagnostics platform and secure healthcare cloud ecosystem."),
    ("Sanofi S.A.", "sanofi.com", "FR", "Healthcare & Immunology", 87000, 0.275, True, ["All-in-AI Healthcare Lead", "Cloud Security Architect", "Regulatory Data Specialist"], True, True, True, "A", [], 0, 70, 0.92, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.89, "'All-in' AI enterprise strategy deploying generative analytics to R&D teams."),
    ("Bayer AG", "bayer.com", "DE", "Life Sciences & Crop Science", 99700, 0.135, True, ["Crop Science Digital Architect", "SAP S/4HANA Migration Lead", "Cyber Incident Specialist"], True, True, True, "B", ["CSP"], 0, 80, 0.89, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.85, "Digital farming platforms (Climate FieldView) and global ERP consolidation."),
    ("TotalEnergies SE", "totalenergies.com", "FR", "Multi-Energy & Renewables", 102000, 0.185, True, ["Renewables Cloud Architect", "OT Infrastructure Security Lead", "Energy Trading Systems SRE"], True, True, True, "A", [], 0, 65, 0.91, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.88, "Industrial IoT predictive maintenance and renewable asset cloud telemetry."),
    ("Shell plc", "shell.com", "UK", "Global Energy & Petrochemicals", 103000, 0.145, True, ["Deep Learning Geoscientist", "Subsurface Cloud Lead", "OT Cyber Defender"], True, True, True, "A", [], 0, 95, 0.92, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.89, "Subsurface cloud analytics on AWS and global digital twin refinery monitoring."),
    ("BP p.l.c.", "bp.com", "UK", "Integrated Energy Operations", 87800, 0.138, True, ["Digital Operations Lead", "Grid Automation Architect", "Industrial Cyber Specialist"], True, True, True, "A", [], 0, 70, 0.90, 0.0, 1.0, 2, 5.0, 1.0, 1.0, 0.87, "Electric vehicle pulse charging network cloud integration and offshore telemetry."),
    ("Rio Tinto Group", "riotinto.com", "UK", "Metals & Automated Mining Operations", 57000, 0.285, True, ["AutoHaul Autonomous Train Lead", "Mining IoT Architect", "OT Security Officer"], True, True, True, "A", [], 0, 45, 0.93, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.91, "AutoHaul autonomous heavy-haul freight network and remote operations centers."),
    ("Volvo Group", "volvogroup.com", "SE", "Commercial Vehicles & Transport Solutions", 104000, 0.142, True, ["Autonomous Solutions Architect", "Connected Truck Cloud Lead", "Zero Trust Engineer"], True, True, True, "A", [], 0, 85, 0.94, 0.0, 1.0, 0, 4.5, 1.0, 1.0, 0.90, "Volvo Autonomous Solutions commercial hub-to-hub autonomous transport rollouts."),
    ("Ericsson", "ericsson.com", "SE", "5G Telecom & Cloud Core Infrastructure", 99950, 0.095, True, ["5G Core Cloud Architect", "Network Automation Lead", "Telecom Cyber Specialist"], True, True, True, "A", [], 0, 520, 0.93, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.89, "Cloud RAN deployments and Open RAN service management orchestration."),
    ("Nokia Corporation", "nokia.com", "FI", "Mobile & Fixed Network Infrastructure", 86700, 0.108, True, ["Private Wireless Systems Architect", "Optical Network Lead", "Security Operations Analyst"], True, True, True, "A", [], 0, 460, 0.92, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.88, "Private 5G wireless networks for industrial mining and airport operations."),
    ("Adyen N.V.", "adyen.com", "NL", "Financial Technology & Global Payments Platform", 4196, 0.465, True, ["Core Payment Systems SRE", "Risk Automation Engineer", "Cyber Resilience Lead"], True, False, True, "A", [], 0, 180, 0.95, 0.0, 1.0, 1, 4.5, 1.0, 1.0, 0.93, "Unified commerce payments expansion with single-stack global authorization engines."),
    ("Spotify Technology S.A.", "spotify.com", "SE", "Audio Streaming & Platform Services", 7400, 0.085, True, ["Backstage Developer Portal Architect", "Audio AI Researcher", "Cloud Reliability Engineer"], True, False, True, "A", [], 0, 620, 0.91, 0.0, 1.0, 2, 4.0, 1.0, 1.0, 0.89, "Backstage open-source platformization and automated audio recommendation AI."),

    # Asia-Pacific Leaders
    ("SoftBank Group Corp.", "softbank.jp", "JP", "Technology Investment & Telecom Infrastructure", 63000, 0.125, True, ["AI Infrastructure Strategist", "Telecom Cloud Architect", "Cyber Operations Lead"], True, True, True, "A", [], 0, 110, 0.92, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.90, "Nationwide Japanese generative AI data center buildout using Nvidia DGX clusters."),
    ("Hitachi, Ltd.", "hitachi.com", "JP", "Social Innovation, OT & Enterprise IT", 322525, 0.088, True, ["Lumada IoT Solution Architect", "Rail Automation Lead", "Cloud Migration Specialist"], True, True, True, "A", [], 0, 310, 0.94, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.91, "Lumada digital solutions driving IT/OT convergence and rail fleet autonomy."),
    ("Keyence Corporation", "keyence.com", "JP", "Factory Automation & Sensors", 10500, 0.525, True, ["Machine Vision Software Engineer", "Factory Automation Lead", "Sensor Systems Architect"], True, True, True, "A", [], 0, 45, 0.95, 0.0, 1.0, 0, 4.5, 1.0, 0.0, 0.93, "High-margin machine vision and 3D laser displacement automation systems."),
    ("Tokyo Electron Limited", "tel.com", "JP", "Semiconductor Production Equipment", 17000, 0.285, True, ["Etch Equipment Software Lead", "CIM Architect", "Equipment IoT Specialist"], True, True, True, "A", [], 0, 60, 0.93, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.91, "Advanced patterning equipment automation for sub-2nm node manufacturing."),
    ("SK Hynix Inc.", "skhynix.com", "KR", "Memory Semiconductors & HBM", 32000, 0.320, True, ["HBM Packaging Automation Lead", "Yield AI Systems Architect", "Semiconductor IT SRE"], True, True, True, "A", [], 0, 85, 0.94, 0.0, 1.0, 2, 4.5, 1.0, 1.0, 0.92, "Leading-edge HBM3E memory fabrication and smart cleanroom logistics automation."),
    ("Hyundai Motor Company", "hyundai.com", "KR", "Automotive & Robotics (Boston Dynamics)", 125000, 0.098, True, ["Metaplant Automation Architect", "Software Defined Vehicle Lead", "Robotics Fleet Specialist"], True, True, True, "A", [], 0, 140, 0.94, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.91, "Georgia Metaplant automated EV production integrating Boston Dynamics robotics."),
    ("Hon Hai Technology Group (Foxconn)", "foxconn.com", "TW", "Contract Electronics Manufacturing", 826608, 0.028, True, ["Smart Factory AI Architect", "Robotic Assembly Lead", "Supply Chain Integrity Officer"], True, True, True, "B", ["CSP"], 0, 180, 0.93, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.89, "Nvidia Omniverse digital twin factories for AI server assembly lines."),
    ("MediaTek Inc.", "mediatek.com", "TW", "Fabless Semiconductor & Wireless SoC", 21800, 0.215, True, ["Dimensity Chipset Architect", "Edge GenAI Engineer", "Compiler Specialist"], True, True, True, "A", [], 0, 110, 0.92, 0.0, 1.0, 2, 4.0, 1.0, 1.0, 0.90, "Dimensity 9400 mobile processors powering on-device multimodal generative AI."),
    ("BHP Group Limited", "bhp.com", "AU", "Diversified Mining & Resources", 80000, 0.445, True, ["Autonomous Drill Systems Lead", "Mine Telemetry Cloud Architect", "Cyber Resilience Specialist"], True, True, True, "A", [], 0, 65, 0.93, 0.0, 1.0, 0, 5.0, 1.0, 1.0, 0.91, "Pilbara automated iron ore operations and remote fleet telematics centers."),
    ("Atlassian Corporation", "atlassian.com", "AU", "Collaboration & Developer Software Tools", 12000, 0.085, True, ["Atlassian Intelligence Architect", "Cloud Migration Specialist", "Security SRE"], True, False, True, "A", [], 0, 480, 0.92, 0.0, 1.0, 2, 4.0, 1.0, 1.0, 0.89, "Jira Cloud platform modernization and Atlassian Intelligence team agents."),

    # Mid-Market Tech & B2B SaaS
    ("Zscaler, Inc.", "zscaler.com", "US", "Zero Trust Cloud Cybersecurity", 7000, 0.125, True, ["Zero Trust Exchange Architect", "SSE Specialist", "Threat Lab Lead"], True, True, True, "A", [], 0, 190, 0.95, 0.0, 1.0, 1, 4.0, 1.0, 1.0, 0.92, "Zero Trust Exchange expanding into branch connectivity and microsegmentation."),
    ("Dynatrace, Inc.", "dynatrace.com", "US", "Software Intelligence & Observability", 4500, 0.185, True, ["Davis AI Platform Architect", "Grail Data Lakehouse Lead", "Cloud SRE"], True, True, True, "A", [], 0, 210, 0.93, 0.0, 1.0, 2, 4.0, 1.0, 1.0, 0.90, "Davis causal AI platform automated root-cause detection for Kubernetes."),
    ("Okta, Inc.", "okta.com", "US", "Identity & Access Management", 6000, 0.085, True, ["Identity Threat Protection Lead", "Customer Identity Architect", "InfoSec Engineer"], True, True, True, "A", [], 0, 240, 0.94, 0.0, 1.0, 1, 4.0, 1.0, 1.0, 0.91, "Identity Threat Protection with Okta AI real-time session response."),
    ("Monday.com Ltd.", "monday.com", "IL", "Work Operating System & Productivity", 2200, 0.115, True, ["WorkOS Platform Architect", "Workflow Automation Specialist", "Cloud SRE"], True, False, True, "A", [], 0, 95, 0.91, 0.0, 1.0, 0, 3.5, 1.0, 1.0, 0.88, "monday WorkOS enterprise cross-departmental workflow orchestration."),
    ("Asana, Inc.", "asana.com", "US", "Enterprise Work Management Platform", 1800, 0.045, True, ["Work Graph AI Architect", "Enterprise Integration Lead", "Security Analyst"], True, False, True, "A", [], 0, 120, 0.89, 0.0, 1.0, 0, 3.5, 1.0, 0.0, 0.86, "Asana Intelligence leveraging Enterprise Work Graph for automated task routing."),
    ("Freshworks Inc.", "freshworks.com", "US", "Customer Engagement & ITSM Software", 5100, 0.085, True, ["Freddy AI Platform Lead", "ITSM Modernization Architect", "Cloud Operations SRE"], True, True, True, "A", [], 0, 180, 0.91, 0.0, 1.0, 0, 4.0, 1.0, 1.0, 0.88, "Freddy AI Copilot integrating automated IT service management ticketing."),
    ("Box, Inc.", "box.com", "US", "Content Cloud & Secure Enterprise Collaboration", 2600, 0.165, True, ["Box AI Platform Lead", "Enterprise Security Architect", "Compliance Specialist"], True, True, True, "A", [], 0, 160, 0.92, 0.0, 1.0, 2, 4.0, 1.0, 0.0, 0.89, "Box AI extraction of unstructured contract metadata and sovereign compliance."),
    ("CyberArk Software Ltd.", "cyberark.com", "IL", "Privileged Access Management & Identity Security", 3200, 0.142, True, ["PAM Platform Architect", "Secrets Management Lead", "Threat Intel Specialist"], True, True, True, "A", [], 0, 140, 0.95, 0.0, 1.0, 1, 4.0, 1.0, 1.0, 0.92, "Privileged access security for machine identities and cloud workloads."),
    ("Tenable Holdings, Inc.", "tenable.com", "US", "Exposure Management & Vulnerability Auditing", 2100, 0.095, True, ["Nessus Platform Architect", "Exposure AI Specialist", "Cloud Security Lead"], True, True, True, "A", [], 0, 110, 0.94, 0.0, 1.0, 1, 4.0, 1.0, 1.0, 0.91, "Tenable One exposure management platform unifying vulnerability metrics."),
    ("Qualys, Inc.", "qualys.com", "US", "Cloud Security & Compliance Platform", 2200, 0.385, True, ["Vulnerability Intelligence Lead", "Cloud Agent Architect", "SOC Specialist"], True, True, True, "A", [], 0, 75, 0.94, 0.0, 1.0, 1, 4.0, 1.0, 1.0, 0.90, "Qualys Enterprise TruRisk Platform aggregating perimeter telemetry."),

    # Real Insolvent / Disqualified Historical Cases
    ("Enron Corporation", "enron.com", "US", "Energy Commodities & Trading", 20000, -1.850, False, [], False, False, True, "F", ["CSP", "Permissions-Policy"], 4, 0, 0.15, 0.0, 0.3, 0, 1.0, 0.0, 0.0, 0.0, "Historic Chapter 11 bankruptcy filing post-accounting fraud."),
    ("Lehman Brothers Holdings Inc.", "lehman.com", "US", "Global Investment Bank", 26000, -2.100, False, [], False, False, True, "F", ["CSP", "Strict-Transport-Security"], 3, 0, 0.10, 0.0, 0.2, 1, 1.0, 0.0, 0.0, 0.0, "Largest Chapter 11 bankruptcy filing in US history in September 2008."),
    ("Washington Mutual (WaMu)", "wamu.com", "US", "Savings & Loan Association", 43000, -1.450, False, [], False, False, True, "F", ["CSP"], 2, 0, 0.12, 0.0, 0.2, 1, 1.0, 0.0, 0.0, 0.0, "FDIC receivership and receivership sale to JPMorgan Chase in 2008."),
    ("WeWork Inc.", "wework.com", "US", "Flexible Workspace & Real Estate", 4400, -0.650, False, [], False, False, True, "D", ["CSP"], 1, 45, 0.35, 0.0, 0.4, 0, 2.0, 0.0, 0.0, 0.0, "Chapter 11 bankruptcy filing in November 2023 with lease restructuring."),
    ("Bed Bath & Beyond Inc.", "bedbathandbeyond.com", "US", "Omnichannel Home Goods Retail", 14000, -0.780, False, [], False, False, True, "D", ["CSP"], 1, 15, 0.25, 0.0, 0.3, 0, 1.5, 0.0, 0.0, 0.0, "Chapter 11 bankruptcy and complete store liquidation in April 2023."),
    ("Lordstown Motors Corp.", "lordstownmotors.com", "US", "Electric Commercial Vehicle OEM", 250, -2.500, False, [], False, False, True, "F", ["CSP"], 0, 5, 0.20, 0.0, 0.3, 0, 1.0, 0.0, 0.0, 0.0, "Chapter 11 filing in Delaware following manufacturing partnership disputes."),
    ("Fisker Inc.", "fiskerinc.com", "US", "Electric Vehicle Production & Design", 1200, -1.950, False, [], False, False, True, "F", ["CSP"], 1, 12, 0.30, 0.0, 0.3, 0, 1.5, 0.0, 0.0, 0.0, "Chapter 11 bankruptcy liquidation in June 2024."),
    ("Thomas Cook Group plc", "thomascook.com", "UK", "Travel Agency & Leisure Airline", 21000, -0.850, False, [], False, False, True, "F", ["CSP"], 2, 0, 0.15, 0.0, 0.3, 0, 1.0, 0.0, 0.0, 0.0, "Compulsory liquidation in UK High Court leaving 150k passengers stranded."),
    ("VanMoof B.V.", "vanmoof.com", "NL", "Electric Bicycle Manufacturer", 700, -1.200, False, [], False, False, True, "F", ["CSP"], 0, 18, 0.40, 0.0, 0.4, 0, 1.5, 0.0, 0.0, 0.0, "Amsterdam District Court bankruptcy declared in July 2023."),
    ("FTI Touristik GmbH", "fti.de", "DE", "Tour Operator & Hospitality Group", 11000, -0.950, False, [], False, False, True, "F", ["CSP"], 1, 10, 0.22, 0.0, 0.3, 0, 1.5, 0.0, 0.0, 0.0, "Insolvency application Munich district court in June 2024.")
]

def main():
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from data.build_global_universe import GLOBAL_COMPANIES
    from data.expanded_enterprises import ADDITIONAL_EUROPEAN_ENTERPRISES

    seen_names = set()
    unified = []

    for c in GLOBAL_COMPANIES:
        name = c["name"].strip()
        if name.lower() not in seen_names:
            seen_names.add(name.lower())
            unified.append(c)

    keys = [
        "name", "domain", "country", "sector", "headcount", "operating_margin", "is_solvent",
        "ats_roles", "has_active_tender", "has_official_ted_award", "has_news_signals",
        "security_grade", "missing_headers", "cisa_count", "github_repos", "semantic_relevance",
        "requires_physical_mismatch", "sector_alignment", "primary_wedge", "tech_stack_breadth",
        "has_enterprise_erp", "has_leadership_catalyst", "hiring_velocity_score", "historical_context"
    ]
    for row in ADDITIONAL_GLOBAL_REGISTRY:
        d = dict(zip(keys, row))
        name = d["name"].strip()
        if name.lower() not in seen_names:
            seen_names.add(name.lower())
            if not d.get("is_solvent", True):
                d["ground_truth_disqualified"] = 1
                d["ground_truth_propensity"] = 0.0
            unified.append(d)

    for c in ADDITIONAL_EUROPEAN_ENTERPRISES:
        name = c["name"].strip()
        if name.lower() not in seen_names:
            seen_names.add(name.lower())
            if not c.get("country"):
                c["country"] = "DE" if "gmbh" in name.lower() or "ag" in name.lower() else "EU"
            unified.append(c)

    print(f"Total unified unique global companies: {len(unified)}")

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write('"""\nGlobal Enterprise Market Universe.\nCurated unique global enterprises across North America, Europe, UK, APAC, and Latin America.\n"""\nfrom typing import Any, Dict, List\n\ntrue = True\nfalse = False\nnull = None\n\n')
        f.write("GLOBAL_ENTERPRISE_UNIVERSE: List[Dict[str, Any]] = ")
        f.write(json.dumps(unified, indent=4))
        f.write("\n")

    print(f"Successfully generated {OUT_FILE} with {len(unified)} distinct companies.")

if __name__ == "__main__":
    main()
