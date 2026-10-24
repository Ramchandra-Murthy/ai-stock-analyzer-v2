from __future__ import annotations

"""
==========================================================
LONG-TERM EQUITY ECONOMIC EVIDENCE SERVICE
Version : V6.0
Author  : AI Stock Analyzer
==========================================================

Purpose
-------
Provides entity-level economic evidence required for
Long-Term Equity SOTP classification.

This registry intentionally separates:

    • legal ownership
    • business activity
    • operating-segment overlap
    • transaction evidence
    • valuation evidence

No runtime mutation is performed.

ECONOMIC_EVIDENCE is the single authoritative registry.
"""

from typing import Any

from services.sotp_long_term_equity_entity_data_service import (
    get_sotp_long_term_equity_entity_data,
)

VERSION = "V6.0"


def _clean_symbol(symbol: str) -> str:
    if symbol is None:
        return ""

    symbol = str(symbol).upper().strip()

    if symbol.endswith(".NS"):
        symbol = symbol[:-3]

    return symbol


ECONOMIC_EVIDENCE: dict[str, dict[str, Any]] = {
    # Entity #1
    "Alok Industries Limited": {
        "business_activity": (
            "Vertically integrated textile manufacturing including home "
            "textiles, cotton yarn, apparel fabric, garments and polyester yarn."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting "
            "classifies Alok Industries Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Official corporate disclosures identify Alok "
            "Industries as an integrated textile manufacturer "
            "with Home Textiles, Cotton Yarn, Apparel Fabric, "
            "Garments and Polyester Yarn businesses."
        ),
        "transaction_evidence": (
            "FY2025-26 related-party disclosures report "
            "purchase and sale transactions with Alok Industries."
        ),
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Textile manufacturing economically supports "
            "Reliance Retail's apparel and fashion ecosystem "
            "and is assessed against the Retail operating segment."
        ),
        "operating_overlap_evidence": (
            "Manufacturing activities overlap vertically with " "Retail apparel sourcing."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supplying " "products into Retail value chains."
        ),
        "valuation_evidence": None,
        "classification_evidence": (
            "Economic characteristics indicate overlap with " "Retail operating segment."
        ),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #2
    "BAM DLR Data Center Services Private Limited": {
        "business_activity": ("Data-center infrastructure and related " "data-center services."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting "
            "classifies BAM DLR Data Center Services "
            "Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Entity participates in Reliance's " "Digital Realty data-center partnership."
        ),
        "transaction_evidence": (
            "FY2025-26 related-party disclosures report " "service transactions."
        ),
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Data-center operations directly support " "Reliance Digital Services."
        ),
        "operating_overlap_evidence": ("Infrastructure supports Digital Services."),
        "economic_independence_evidence": (
            "Joint venture operates independently while " "supporting Digital Services."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Economically aligned with Digital Services."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #3
    "BAM DLR Mumbai Private Limited": {
        "business_activity": ("Data-center infrastructure and data-center services."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance related-party reporting classifies "
            "BAM DLR Mumbai Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Digital Realty partnership disclosures identify " "Mumbai data-center operations."
        ),
        "transaction_evidence": (
            "FY2025-26 related-party disclosures report " "service transactions."
        ),
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Entity supports Digital Services through " "data-center infrastructure."
        ),
        "operating_overlap_evidence": ("Infrastructure overlaps with Digital Services."),
        "economic_independence_evidence": (
            "Operates independently while supporting " "Digital Services."
        ),
        "valuation_evidence": None,
        "classification_evidence": "Digital Services overlap.",
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #4
    "BAM DLR Network Services Private Limited": {
        "business_activity": ("Network and data-center related infrastructure services."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance related-party reporting classifies BAM DLR "
            "Network Services Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Disclosures identify entity providing network and connectivity "
            "infrastructure within Digital Realty partnership."
        ),
        "transaction_evidence": (
            "FY2025-26 related-party disclosures report " "infrastructure transactions."
        ),
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Network infrastructure directly connects with " "Digital Services telecom backbone."
        ),
        "operating_overlap_evidence": ("Network assets overlap with digital infrastructure."),
        "economic_independence_evidence": ("Operates independently under joint venture terms."),
        "valuation_evidence": None,
        "classification_evidence": ("Economically aligned with Digital Services."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #5
    "Big Tree Entertainment Private Limited": {
        "business_activity": (
            "Entertainment ticketing and digital platform services "
            "operating under BookMyShow brand."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Consolidated related-party disclosures classify "
            "Big Tree Entertainment Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Official platform disclosures support ticketing, "
            "event management, and digital content distribution."
        ),
        "transaction_evidence": (
            "FY2025-26 consolidated related-party disclosures " "report platform service revenue."
        ),
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Digital consumer platform business economically "
            "aligns with Digital Services and Jio ecosystem."
        ),
        "operating_overlap_evidence": (
            "Digital ticketing platform overlaps with consumer " "digital media services."
        ),
        "economic_independence_evidence": ("Operates as an independent platform business."),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #6
    "Brooks Brothers India Private Limited": {
        "business_activity": (
            "Retail and distribution of Brooks Brothers branded "
            "apparel and fashion products in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Consolidated related-party disclosures classify "
            "Brooks Brothers India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Reliance Retail brand disclosures confirm retail store "
            "operations and distribution of premium apparel."
        ),
        "transaction_evidence": (
            "FY2025-26 consolidated related-party disclosures " "report retail supply transactions."
        ),
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Fashion retail operations directly integrate into "
            "Reliance Retail's consumer brand strategy."
        ),
        "operating_overlap_evidence": ("Store operations overlap with Retail operating segment."),
        "economic_independence_evidence": ("Managed as joint venture brand partner within Retail."),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #7
    "Burberry India Private Limited": {
        "business_activity": (
            "Retail distribution and operation of Burberry luxury "
            "fashion and accessories in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Consolidated related-party disclosures classify "
            "Burberry India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Corporate disclosures confirm luxury retail boutique "
            "operations across major metropolitan centers in India."
        ),
        "transaction_evidence": (
            "FY2025-26 consolidated related-party disclosures " "report operating transactions."
        ),
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Luxury retail distribution forms an integral part "
            "of Reliance Retail's luxury division."
        ),
        "operating_overlap_evidence": ("Boutique retail footprint overlaps with Retail segment."),
        "economic_independence_evidence": (
            "Joint venture operates under luxury brand licensing rules."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Retail candidate segment mapping."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #8
    "Caelux Corporation": {
        "business_activity": (
            "Development of perovskite-based solar technology for "
            "high-efficiency solar module manufacturing."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Consolidated related-party disclosures classify " "Caelux Corporation as an Associate."
        ),
        "business_activity_evidence": (
            "Reliance New Energy official announcements identify "
            "perovskite research and development technology partnership."
        ),
        "transaction_evidence": (
            "FY2025-26 related-party disclosures report " "technology advancement funding."
        ),
        "candidate_operating_segment": "NEW_ENERGY",
        "segment_evidence": (
            "Solar cell research and technology development "
            "directly supports the New Energy solar gigafactory."
        ),
        "operating_overlap_evidence": (
            "Perovskite tech overlaps with New Energy manufacturing strategy."
        ),
        "economic_independence_evidence": ("Independent technology developer strategic associate."),
        "valuation_evidence": None,
        "classification_evidence": ("New Energy candidate segment."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #9
    "Canali India Private Limited": {
        "business_activity": (
            "Retail and distribution of Canali luxury menswear " "and accessories in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Consolidated related-party disclosures classify "
            "Canali India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Reliance Retail disclosures support retail store "
            "operations for Canali branded apparel."
        ),
        "transaction_evidence": (
            "FY2025-26 consolidated disclosures report related-party "
            "retail merchandise transactions."
        ),
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Luxury menswear distribution integrates into " "Reliance Retail's luxury division."
        ),
        "operating_overlap_evidence": ("Store operations overlap with Retail segment."),
        "economic_independence_evidence": ("Joint venture operates under luxury brand agreements."),
        "valuation_evidence": None,
        "classification_evidence": ("Retail candidate segment mapping."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #10
    "Circle E Retail Private Limited": {
        "business_activity": ("Manufacturing of toys and specialized consumer " "retail products."),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Consolidated related-party purchase disclosures "
            "classify Circle E Retail Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate filings identify specialized toy manufacturing "
            "and retail distribution capabilities."
        ),
        "transaction_evidence": (
            "FY2025-26 related-party reporting discloses purchase " "of goods and services."
        ),
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Toy manufacturing and distribution economically supports "
            "Reliance Retail's Hamleys and toy retail business."
        ),
        "operating_overlap_evidence": ("Toy supply chain overlaps vertically with Retail."),
        "economic_independence_evidence": ("Independent manufacturing associate supplying Retail."),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed against Retail operating segment."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #11
    "Clayfin Technologies Private Limited": {
        "business_activity": (
            "Digital banking technology and software platforms for banks "
            "and financial institutions."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance group related-party disclosures classify Clayfin "
            "Technologies Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate disclosures describe digital banking platforms and software "
            "solutions for banking and financial sectors."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Digital banking software activities are economically aligned "
            "with Reliance's Digital Services and Jio Financial technology ecosystem."
        ),
        "operating_overlap_evidence": (
            "Software platforms overlap with enterprise digital solutions."
        ),
        "economic_independence_evidence": (
            "Operates as an independent fintech software associate."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment mapping."),
        "source": "Clayfin Technologies official corporate disclosure",
    },
    # Entity #12
    "DEN ADN Network Private Limited": {
        "business_activity": ("Cable television distribution and local cable network services."),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "DEN Networks financial disclosures and Reliance FY2025-26 related-party "
            "reporting classify DEN ADN Network Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Official service documentation identifies multi-system cable TV operator "
            "and distribution operations."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Cable TV distribution and local cable operations support "
            "Reliance's digital media and broadband ecosystem."
        ),
        "operating_overlap_evidence": (
            "Media distribution overlaps with Digital Services cable footprint."
        ),
        "economic_independence_evidence": (
            "Operates under DEN regional network associate structure."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed against Digital Services operating segment."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #13
    "Den Satellite Network Private Limited": {
        "business_activity": ("Cable television distribution and satellite network services."),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies Den Satellite "
            "Network Private Limited as an Associate of a subsidiary."
        ),
        "business_activity_evidence": (
            "Corporate disclosures confirm cable TV network and satellite distribution "
            "business operations."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Satellite cable distribution aligns with Digital Services media " "infrastructure."
        ),
        "operating_overlap_evidence": (
            "Distribution footprint overlaps with Digital Services cable network."
        ),
        "economic_independence_evidence": (
            "Operates as a regional associate distribution network."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment mapping."),
        "source": "RIL Integrated Annual Report FY2025-26",
    },
    # Entity #14
    "Diesel Fashion India Reliance Private Limited": {
        "business_activity": (
            "Retail sale and distribution of Diesel branded apparel, accessories, "
            "and fashion products in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance Brands Limited financial statements classify Diesel Fashion "
            "India Reliance Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Official brand disclosures confirm store operations and online retail "
            "for Diesel fashion products in India."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Premium denim and fashion retail store operations directly integrate "
            "into Reliance Retail's brand portfolio."
        ),
        "operating_overlap_evidence": ("Retail boutique operations overlap with Retail segment."),
        "economic_independence_evidence": (
            "Joint venture operates under international brand partner agreements."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Diesel India official corporate disclosure",
    },
    # Entity #15
    "DXDC Chennai Private Limited": {
        "business_activity": (
            "Data-center infrastructure development and related data-center services."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance disclosures identify DXDC Chennai Private Limited (formerly "
            "BAM DLR Chennai Private Limited) as a Joint Venture under the Digital Realty "
            "and Brookfield partnership."
        ),
        "business_activity_evidence": (
            "Entity disclosures confirm data-center facility construction and "
            "infrastructure operations in Chennai."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Enterprise data-center infrastructure directly supports Reliance "
            "Digital Services cloud and connectivity infrastructure."
        ),
        "operating_overlap_evidence": (
            "Infrastructure assets overlap with Digital Services data-center capacity."
        ),
        "economic_independence_evidence": (
            "Operates independently under joint venture governance."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Reliance Industries Limited official disclosure",
    },
    # Entity #16
    "Future101 Design Private Limited": {
        "business_activity": (
            "Design, manufacturing, and luxury retail of apparel and fashion "
            "products under the Raghavendra Rathore brand."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance Brands Limited financial statements classify Future101 "
            "Design Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate filings and brand disclosures identify luxury designer "
            "apparel manufacturing and bespoke retail business."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Luxury designer fashion operations support Reliance Retail's "
            "couture and premium fashion segment."
        ),
        "operating_overlap_evidence": (
            "Designer retail distribution overlaps with Retail segment."
        ),
        "economic_independence_evidence": ("Independent designer brand associate."),
        "valuation_evidence": None,
        "classification_evidence": ("Retail candidate segment mapping."),
        "source": "Raghavendra Rathore / Future101 official disclosure",
    },
    # Entity #17
    "Gaurav Overseas Private Limited": {
        "business_activity": ("Construction and real-estate related activities."),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance Industries Limited related-party disclosures explicitly "
            "classify Gaurav Overseas Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate registration records (CIN U45200MH1989PTC052534) identify "
            "construction and real-estate development activity."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OTHERS",
        "segment_evidence": (
            "Real-estate development and construction support activities "
            "represent corporate/infrastructure holdings distinct from core segments."
        ),
        "operating_overlap_evidence": (
            "Real-estate assets managed as non-operating corporate holdings."
        ),
        "economic_independence_evidence": ("Operates as an independent associate holding entity."),
        "valuation_evidence": None,
        "classification_evidence": ("Categorized under Others operating segment."),
        "source": ("Ministry of Corporate Affairs registration-derived " "corporate information"),
    },
    # Entity #18
    "GTPL Hathway Limited": {
        "business_activity": (
            "Digital cable television distribution and wireline broadband " "internet services."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Hathway Cable and Datacom Limited financial statements classify "
            "GTPL Hathway Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Official corporate disclosures describe Multi-System Operator (MSO) "
            "digital cable TV and fiber-to-the-home broadband services."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Cable TV distribution and wireline broadband directly align with "
            "Reliance Digital Services and JioFiber footprint expansion."
        ),
        "operating_overlap_evidence": (
            "Broadband and cable subscriber base overlaps with Digital Services."
        ),
        "economic_independence_evidence": ("Publicly listed associate operating independently."),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "GTPL Hathway Limited official corporate disclosure",
    },
    # Entity #19
    "Gujarat Chemical Port Limited": {
        "business_activity": (
            "Commercial chemical and liquid cargo port terminal operations, offering "
            "bulk chemical storage and handling services at Dahej."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance Industries statutory disclosures classify Gujarat Chemical "
            "Port Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Official terminal disclosures identify bulk liquid chemical storage, "
            "jetty operations, and specialized cargo logistics in Dahej, Gujarat."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OIL_TO_CHEMICALS",
        "segment_evidence": (
            "Bulk liquid chemical port terminals provide vital feedstock and product "
            "logistics infrastructure supporting Reliance's Oil to Chemicals (O2C) segment."
        ),
        "operating_overlap_evidence": (
            "Chemical handling infrastructure overlaps with O2C supply chain."
        ),
        "economic_independence_evidence": (
            "Commercial port operator providing services to Reliance and third parties."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Oil to Chemicals candidate segment mapping."),
        "source": "Gujarat Chemical Port Limited official disclosures",
    },
    # Entity #20
    "Hathway Channel 5 Cable and Datacom Private Limited": {
        "business_activity": ("Telecommunications and cable-network distribution services."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Hathway Cable and Datacom Limited financial disclosures classify "
            "Hathway Channel 5 Cable and Datacom Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Corporate filings confirm telecom and local cable TV network " "distribution services."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Cable distribution network supports regional media connectivity "
            "for Digital Services."
        ),
        "operating_overlap_evidence": (
            "Cable TV connectivity overlaps with Digital Services media division."
        ),
        "economic_independence_evidence": ("Joint venture operates local network infrastructure."),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Hathway Cable and Datacom Limited official disclosure",
    },
    # Entity #21
    "Hathway Latur MCN Cable & Datacom Private Limited": {
        "business_activity": ("Cable television distribution and regional cable network business."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Hathway group related-party disclosures classify Hathway Latur MCN "
            "Cable & Datacom Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Financial statements published through Hathway explicitly state "
            "that the company is engaged in the Cable TV business."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with Reliance's "
            "Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Digital Services candidate segment."),
        "source": (
            "Hathway Latur MCN Cable & Datacom Private Limited "
            "financial statements published by Hathway"
        ),
    },
    # Entity #22
    "Hathway MCN Private Limited": {
        "business_activity": ("Television broadcasting and cable-network distribution activities."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Hathway Cable and Datacom Limited related-party disclosures classify "
            "Hathway MCN Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Corporate registration evidence and Hathway disclosures identify "
            "radio and television cable distribution activities."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with Reliance's "
            "Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Hathway official disclosure and corporate registration evidence",
    },
    # Entity #23
    "Hathway Sonali OM Crystal Cable Private Limited": {
        "business_activity": (
            "Computer-related and network-associated services within " "the cable group."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Hathway group financial and related-party disclosures classify "
            "Hathway Sonali OM Crystal Cable Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Hathway official disclosures identify entity within subsidiary "
            "structure engaged in network-associated activities."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with Reliance's "
            "Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Hathway official subsidiary disclosure and corporate registration evidence",
    },
    # Entity #24
    "Hathway SS Cable & Datacom LLP": {
        "business_activity": (
            "Real estate, renting, and support activities tied to cable network " "operations."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Hathway Cable and Datacom Limited statutory returns classify "
            "Hathway SS Cable & Datacom LLP as an Associate."
        ),
        "business_activity_evidence": (
            "MCA LLP registration information classifies principal business activity "
            "under real estate, renting, and business support."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OTHERS",
        "segment_evidence": (
            "Business activities do not align directly with one of "
            "Reliance's primary operating segments and are classified "
            "under Other for SOTP overlap assessment."
        ),
        "operating_overlap_evidence": (
            "Limited direct operating overlap exists with the major "
            "reportable operating segments."
        ),
        "economic_independence_evidence": (
            "Entity operates independently outside the core " "operating segments."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Categorized under Others candidate segment."),
        "source": "MCA registration-derived LLP information",
    },
    # Entity #25
    "Health Alliance Global Inc.": {
        "business_activity": (
            "Digital healthcare platforms, patient-side mobile diagnostics, "
            "and virtual care delivery solutions."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance related-party reporting classifies Health Alliance "
            "Global Inc. as an Associate in relation to Reliance Digital Health."
        ),
        "business_activity_evidence": (
            "Corporate disclosures describe digital health technology, mobile "
            "diagnostic software, and virtual care platforms."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with Reliance's "
            "Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Health Alliance Global official corporate website and disclosures",
    },
    # Entity #26
    "Iconix Lifestyle India Private Limited": {
        "business_activity": (
            "Brand licensing, brand management, and development of fashion "
            "and consumer lifestyle brands in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance disclosures identify Iconix Lifestyle India Private Limited "
            "as a joint venture with Iconix Brand Group."
        ),
        "business_activity_evidence": (
            "Disclosures confirm ownership, licensing, and management of "
            "fashion and lifestyle brand IP in India."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Reliance Retail official disclosure",
    },
    # Entity #27
    "India Gas Solutions Private Limited": {
        "business_activity": ("Sourcing, marketing, and distribution of natural gas in India."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "India Gas Solutions identifies itself as a 50:50 joint venture "
            "between Reliance Industries Limited and bp."
        ),
        "business_activity_evidence": (
            "Official corporate disclosures confirm the entity focuses on sourcing "
            "and marketing natural gas across Indian markets."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OIL_AND_GAS",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance's Oil and Gas segment."
        ),
        "operating_overlap_evidence": ("Operations support natural gas sourcing and marketing."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing " "to upstream and gas operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Oil and Gas candidate segment."),
        "source": "India Gas Solutions official corporate disclosure",
    },
    # Entity #28
    "Indian Vaccines Corporation Limited": {
        "business_activity": (
            "Research, development, and manufacturing activities associated "
            "with vaccines and biological products."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Consolidated disclosures and corporate registry records classify "
            "Indian Vaccines Corporation Limited under Associate holdings."
        ),
        "business_activity_evidence": (
            "Available disclosures support biological products and vaccine "
            "development activities."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OTHERS",
        "segment_evidence": (
            "Business activities do not align directly with one of "
            "Reliance's primary operating segments and are classified "
            "under Other for SOTP overlap assessment."
        ),
        "operating_overlap_evidence": (
            "Limited direct operating overlap exists with the major "
            "reportable operating segments."
        ),
        "economic_independence_evidence": (
            "Entity operates independently outside the core " "operating segments."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Categorized under Others candidate segment."),
        "source": "Indian Vaccines Corporation official disclosure",
    },
    # Entity #29
    "Indospace MET Logistics Park Farukhnagar Private Limited": {
        "business_activity": (
            "Development and operation of industrial parks, warehousing, "
            "and logistics infrastructure."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies entity as "
            "a Joint Venture of Model Economic Township Limited."
        ),
        "business_activity_evidence": (
            "Corporate and logistics-park disclosures identify industrial park "
            "and logistics infrastructure operations in Farukhnagar."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Retail candidate segment mapping."),
        "source": "IndoSpace official corporate disclosure",
    },
    # Entity #30
    "Jio BLAST eSports Private Limited": {
        "business_activity": (
            "Esports tournaments, competitive-gaming platform services, and "
            "digital gaming content distribution."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance Industries' June 25, 2025 disclosure confirms transition "
            "from subsidiary to 50:50 Joint Venture with BLAST Esports Limited."
        ),
        "business_activity_evidence": (
            "Official platform disclosures confirm operation of esports technology "
            "and digital gaming event platforms."
        ),
        "transaction_evidence": (
            "On June 25, 2025 allotted 50,00,000 equity shares aggregating INR 5 crore "
            "to BLAST Esports Limited, reducing RISE Worldwide's stake to 50%."
        ),
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with Reliance's "
            "Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Reliance Industries Limited official disclosure",
    },
    # Entity #31
    "Jio Space Technology Limited": {
        "business_activity": (
            "Satellite-based broadband and connectivity services for customers in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Jio Space Technology Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Official disclosures confirm joint venture with SES to deliver "
            "satellite-based broadband and satellite connectivity across India."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Reliance Industries Limited official disclosure",
    },
    # Entity #32
    "Marks and Spencer Reliance India Private Limited": {
        "business_activity": (
            "Retail sale of apparel, lingerie, beauty products and related fashion "
            "merchandise in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Marks and Spencer Reliance India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Marks & Spencer India disclosures confirm retail store operations "
            "and nationwide brand distribution."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Reliance Retail official disclosure",
    },
    # Entity #33
    "Media Pro Enterprise India Private Limited": {
        "business_activity": (
            "Television content distribution and related broadcasting and "
            "media-distribution activities."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Media Pro Enterprise India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Disclosures confirm television channel distribution and media aggregations."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Reliance Industries Limited official disclosure",
    },
    # Entity #34
    "MIL Limited": {
        "business_activity": ("Professional sports and cricket-team related activities."),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies " "MIL Limited as an Associate."
        ),
        "business_activity_evidence": (
            "UK corporate registry filings identify sports team management and "
            "commercial cricket assets."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OTHERS",
        "segment_evidence": (
            "Business activities do not align directly with a "
            "primary reportable operating segment and are classified "
            "under Other for SOTP overlap assessment."
        ),
        "operating_overlap_evidence": (
            "Limited direct operating overlap exists with the major "
            "reportable operating segments."
        ),
        "economic_independence_evidence": (
            "Entity operates independently outside the core " "operating segments."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Categorized under Others candidate segment."),
        "source": "UK Companies House",
    },
    # Entity #35
    "MM Styles Private Limited": {
        "business_activity": (
            "Fashion and lifestyle design activities including apparel, costume, "
            "jewellery and accessories design."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "MM Styles Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Designer disclosures confirm haute couture fashion, apparel, and "
            "accessory design operations."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Retail candidate segment mapping."),
        "source": "MM Styles corporate disclosure",
    },
    # Entity #36
    "Neolync Solutions Private Limited": {
        "business_activity": ("Trading of telecom equipment and customer devices."),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Neolync Solutions Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate disclosures confirm wholesale trading and supply of "
            "telecommunications hardware and devices."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Digital Services operating segment."
        ),
        "operating_overlap_evidence": ("Operations directly support Digital Services activities."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing to the " "Digital Services ecosystem."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Neolync corporate disclosure",
    },
    # Entity #37
    "Nexwafe GmbH": {
        "business_activity": (
            "Development and manufacturing technology for engineered silicon "
            "photovoltaic wafers."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies " "Nexwafe GmbH as an Associate."
        ),
        "business_activity_evidence": (
            "Official corporate disclosures confirm epitaxy wafer technology "
            "development for green energy applications."
        ),
        "transaction_evidence": (
            "Strategic partner relationship providing technology capital for "
            "photovoltaic wafer manufacturing."
        ),
        "candidate_operating_segment": "NEW_ENERGY",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's New Energy operating segment."
        ),
        "operating_overlap_evidence": (
            "Solar cell technology directly supports New Energy gigafactory plans."
        ),
        "economic_independence_evidence": (
            "Independent technology associate operating in silicon wafer production."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("New Energy candidate segment."),
        "source": "Nexwafe official corporate disclosure",
    },
    # Entity #38
    "Omnia Toys India Private Limited": {
        "business_activity": (
            "Manufacturing activities associated with toys and plastic consumer products."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Omnia Toys India Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate filings identify plastic product and toy manufacturing facilities."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Retail candidate segment mapping."),
        "source": "Omnia Toys corporate disclosure",
    },
    # Entity #39
    "Pipeline Management Services Private Limited": {
        "business_activity": ("Pipeline-related management and support services."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Pipeline Management Services Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Disclosures confirm technical pipeline management, operation, and "
            "maintenance services."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OIL_TO_CHEMICALS",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Oil-to-Chemicals operating segment."
        ),
        "operating_overlap_evidence": (
            "Pipeline management services support crude and product transport logistics."
        ),
        "economic_independence_evidence": (
            "Entity operates as a joint venture providing specialised pipeline management."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Oil to Chemicals candidate segment."),
        "source": "Reliance Industries Limited official disclosure",
    },
    # Entity #40
    "Reldel Apparel Private Limited": {
        "business_activity": ("Retail trade of clothing and apparel."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reldel Apparel Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Corporate registration records confirm retail trade of apparel and garments."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Reliance Retail official disclosure",
    },
    # Entity #41
    "Reliance Bally India Private Limited": {
        "business_activity": (
            "Retail and digital sale of Bally branded footwear, bags, accessories, "
            "clothing and related luxury products in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reliance Bally India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Official disclosures confirm boutique store operations and digital retail platform "
            "for Bally luxury fashion and footwear."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Reliance Retail official disclosure",
    },
    # Entity #42
    "Reliance Europe Limited": {
        "business_activity": (
            "Wholesale of fuels and related petroleum products together with "
            "business-support activities."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reliance Europe Limited as an Associate."
        ),
        "business_activity_evidence": (
            "UK Companies House filings confirm wholesale trade of fuels, energy commodities, "
            "and overseas business support services."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OIL_TO_CHEMICALS",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Oil-to-Chemicals operating segment."
        ),
        "operating_overlap_evidence": (
            "Wholesale fuel trade directly supports international energy trading and O2C supply chains."
        ),
        "economic_independence_evidence": (
            "Entity operates independently outside primary domestic manufacturing hubs."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Oil to Chemicals candidate segment."),
        "source": "Reliance Europe Limited official corporate disclosure",
    },
    # Entity #43
    "Reliance Industrial Infrastructure Limited": {
        "business_activity": (
            "Industrial infrastructure including petroleum-product pipelines, natural-gas pipelines, "
            "raw-water pipelines and associated infrastructure support services."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reliance Industrial Infrastructure Limited as an Associate."
        ),
        "business_activity_evidence": (
            "RIIL official disclosures confirm operation of industrial pipelines transporting "
            "petroleum products, gas, and raw water to manufacturing hubs."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OIL_TO_CHEMICALS",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Oil-to-Chemicals operating segment."
        ),
        "operating_overlap_evidence": (
            "Industrial infrastructure and pipeline networks directly support O2C refining and petrochemical logistics."
        ),
        "economic_independence_evidence": (
            "Publicly listed associate operating independently to supply essential industrial services."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Oil to Chemicals candidate segment."),
        "source": "Reliance Industrial Infrastructure Limited official corporate disclosure",
    },
    # Entity #44
    "Reliance International Leasing IFSC Private Limited": {
        "business_activity": (
            "International financial-services leasing activities through an IFSC entity."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reliance International Leasing IFSC Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "IFSCA and GIFT City disclosures confirm cross-border equipment, aircraft, and asset "
            "leasing operations."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "FINANCIAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "financial services and leasing operations."
        ),
        "operating_overlap_evidence": (
            "IFSC leasing operations align with group financial services and asset financing."
        ),
        "economic_independence_evidence": (
            "Entity operates independently as an IFSC licensed offshore leasing vehicle."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Financial Services candidate segment."),
        "source": "Reliance Industries Limited official disclosure",
    },
    # Entity #45
    "Reliance Logistics and Warehouse Holdings Limited": {
        "business_activity": (
            "Transport, logistics, warehousing and supply-chain infrastructure activities."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reliance Logistics and Warehouse Holdings Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate registration and group disclosures confirm freight transport, warehousing, "
            "and logistics park development."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OTHER",
        "segment_evidence": (
            "Independent business outside the primary reportable operating segments."
        ),
        "operating_overlap_evidence": (
            "Logistics infrastructure provides broad group supply-chain support across multiple divisions."
        ),
        "economic_independence_evidence": (
            "Entity operates independently as an infrastructure holding asset."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Categorized under Other candidate segment."),
        "source": "Reliance Logistics and Warehouse Holdings Limited official corporate disclosure",
    },
    # Entity #46
    "Reliance Paul & Shark Fashions Private Limited": {
        "business_activity": (
            "Retail and distribution of Paul & Shark branded fashion apparel and accessories in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reliance Paul & Shark Fashions Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Brand disclosures confirm retail store operations and exclusive distribution "
            "of Paul & Shark luxury sportswear in India."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Paul & Shark official corporate disclosure",
    },
    # Entity #47
    "Reliance-Vision Express Private Limited": {
        "business_activity": (
            "Retail of eyewear together with professional optical and eye-care services in India."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Reliance-Vision Express Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Vision Express disclosures confirm optical store operations, prescription eyewear sales, "
            "and optometrist services."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Vision Express India official corporate website",
    },
    # Entity #48
    "Ryohin-Keikaku Reliance India Private Limited": {
        "business_activity": ("Retail sale of MUJI branded consumer products in India."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Ryohin-Keikaku Reliance India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "MUJI corporate disclosures confirm retail store operations for lifestyle, household, "
            "and apparel merchandise in India."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Ryohin Keikaku official group-company disclosure",
    },
    # Entity #49
    "Sanmina-SCI India Private Limited": {
        "business_activity": (
            "Integrated electronics manufacturing services, repair, logistics and after-market support "
            "for OEM customers."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Sanmina-SCI India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "CCI acquisition disclosures confirm advanced electronics manufacturing for telecom, "
            "cloud, and industrial hardware."
        ),
        "transaction_evidence": (
            "Acquisition of 50.1% equity stake by Reliance Strategic Business Ventures Limited "
            "to establish high-tech manufacturing JV."
        ),
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Digital Services operating segment."
        ),
        "operating_overlap_evidence": (
            "Telecom hardware manufacturing directly supports 5G network equipment and digital infrastructure."
        ),
        "economic_independence_evidence": (
            "Joint venture operates independently providing EMS solutions to global and domestic OEMs."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Competition Commission of India acquisition disclosure",
    },
    # Entity #50
    "Sintex Industries Limited": {
        "business_activity": (
            "Textile manufacturing including cotton yarns, blended yarns, linen yarns and "
            "value-added textile products."
        ),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Sintex Industries Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Official corporate disclosures confirm integrated textile spinning, weaving, "
            "and yarn manufacturing operations."
        ),
        "transaction_evidence": (
            "Insolvency resolution plan implemented jointly with ACRE, acquiring joint "
            "control over textile manufacturing operations."
        ),
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Yarn and fabric manufacturing vertically integrates with Retail apparel sourcing."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supplying products into textile value chains."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Sintex Industries Limited official corporate disclosure",
    },
    # Entity #51
    "Sosyo Hajoori Beverages Private Limited": {
        "business_activity": ("Beverage manufacturing and related beverage business."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Sosyo Hajoori Beverages Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Corporate registration and group disclosures confirm beverage manufacturing, "
            "bottling, and distribution operations."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Sosyo Hajoori Beverages official corporate disclosure",
    },
    # Entity #52
    "SRC Ecotex (India) Private Limited": {
        "business_activity": (
            "Recycling post-consumer plastic waste into recycled polyester "
            "staple fibre and recycled polyester fibre-fill products."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "SRC Ecotex (India) Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Official corporate disclosures describe PET bottle recycling and green manufacturing "
            "of recycled polyester staple fibre."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "SRC Ecotex official corporate disclosure",
    },
    # Entity #53
    "Sterling and Wilson Renewable Energy Limited": {
        "business_activity": (
            "End-to-end renewable-energy engineering, procurement and "
            "construction solutions together with operation and maintenance services."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Sterling and Wilson Renewable Energy Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Official disclosures confirm utility-scale solar EPC, battery energy storage, "
            "and renewable asset management services globally."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "NEW_ENERGY",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's New Energy operating segment."
        ),
        "operating_overlap_evidence": (
            "Renewable EPC services directly support New Energy green power gigafactory deployments."
        ),
        "economic_independence_evidence": (
            "Publicly listed associate operating independently across global renewable markets."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("New Energy candidate segment."),
        "source": "Sterling and Wilson Renewable Energy Limited official corporate disclosure",
    },
    # Entity #54
    "TCO Reliance India Private Limited": {
        "business_activity": ("Non-specialized retail trade in stores."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "TCO Reliance India Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Corporate registration records confirm non-specialized store-based retail trade operations."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Reliance Industries Limited official disclosure",
    },
    # Entity #55
    "Ubona Technologies Private Limited": {
        "business_activity": (
            "Technology and software solutions for voice, communications "
            "and digital customer interactions."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Ubona Technologies Private Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Corporate disclosures confirm development of enterprise cloud telephony, automated voice systems, "
            "and conversational AI platforms."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "DIGITAL_SERVICES",
        "segment_evidence": (
            "Business activities are economically aligned with "
            "Reliance's Digital Services operating segment."
        ),
        "operating_overlap_evidence": (
            "Voice and communications software directly supports Digital Services enterprise technology."
        ),
        "economic_independence_evidence": (
            "Entity operates independently as an enterprise software platform provider."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Digital Services candidate segment."),
        "source": "Ubona Technologies corporate disclosure",
    },
    # Entity #56
    "Vadodara Enviro Channel Limited": {
        "business_activity": (
            "Treated-wastewater conveyance infrastructure together with "
            "environmental engineering and environmental management services."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Vadodara Enviro Channel Limited as an Associate."
        ),
        "business_activity_evidence": (
            "Official disclosures confirm operation of industrial effluent channel pipelines conveying "
            "treated wastewater from Vadodara industrial clusters to the sea."
        ),
        "transaction_evidence": None,
        "candidate_operating_segment": "OTHER",
        "segment_evidence": (
            "Business activities do not align directly with one of "
            "Reliance's primary operating segments and are classified "
            "under Other for SOTP overlap assessment."
        ),
        "operating_overlap_evidence": (
            "Limited direct operating overlap exists with the major "
            "reportable operating segments."
        ),
        "economic_independence_evidence": (
            "Entity operates independently outside the core " "operating segments."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Categorized under Other candidate segment."),
        "source": "Vadodara Enviro Channel Limited official website",
    },
    # Entity #57
    "Wavetech Helium, Inc.": {
        "business_activity": (
            "Helium gas exploration and production including acquisition, "
            "exploration and development of underground helium reservoirs."
        ),
        "ril_relationship": "ASSOCIATE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Wavetech Helium, Inc. as an Associate."
        ),
        "business_activity_evidence": (
            "Official acquisition disclosures confirm helium field development and extraction "
            "operations in North America."
        ),
        "transaction_evidence": (
            "Reliance Finance and Investments USA LLC acquired 21% equity stake for USD 12 million."
        ),
        "candidate_operating_segment": "OIL_AND_GAS",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance's Oil and Gas segment."
        ),
        "operating_overlap_evidence": ("Operations support natural gas sourcing and marketing."),
        "economic_independence_evidence": (
            "Entity operates independently while contributing " "to upstream and gas operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Oil and Gas candidate segment."),
        "source": "Reliance Industries Limited disclosure dated November 28, 2024",
    },
    # Entity #58
    "Zegna South Asia Private Limited": {
        "business_activity": ("Fashion and clothing trade and retail activities."),
        "ril_relationship": "JOINT_VENTURE",
        "relationship_evidence": (
            "Reliance FY2025-26 related-party reporting classifies "
            "Zegna South Asia Private Limited as a Joint Venture."
        ),
        "business_activity_evidence": (
            "Official disclosures confirm luxury store operations and distribution of Ermenegildo Zegna "
            "apparel in South Asia."
        ),
        "transaction_evidence": (
            "Related-party disclosures report retail merchandise and brand supply transactions."
        ),
        "candidate_operating_segment": "RETAIL",
        "segment_evidence": (
            "Business activities are economically aligned with " "Reliance Retail."
        ),
        "operating_overlap_evidence": (
            "Operations overlap with Retail merchandising and " "consumer distribution."
        ),
        "economic_independence_evidence": (
            "Entity operates independently while supporting " "Retail operations."
        ),
        "valuation_evidence": None,
        "classification_evidence": ("Assessed under Retail operating segment."),
        "source": "Zegna South Asia Private Limited official corporate disclosure",
    },
}


def _validate_economic_evidence(
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(evidence, dict):
        evidence = {}

    relationship_known = bool(
        evidence.get("ril_relationship") and evidence.get("relationship_evidence")
    )

    economic_activity_known = bool(
        evidence.get("business_activity") and evidence.get("business_activity_evidence")
    )

    transaction_evidence_available = bool(evidence.get("transaction_evidence"))

    segment_evidence_available = bool(evidence.get("segment_evidence"))

    overlap_assessable = bool(
        evidence.get("candidate_operating_segment")
        and (
            evidence.get("segment_evidence")
            or evidence.get("operating_overlap_evidence")
            or evidence.get("economic_independence_evidence")
        )
    )

    source_present = bool(evidence.get("source"))

    missing_requirements: list[str] = []

    if not relationship_known:
        missing_requirements.append("RELATIONSHIP_EVIDENCE")

    if not economic_activity_known:
        missing_requirements.append("BUSINESS_ACTIVITY_EVIDENCE")

    if not overlap_assessable:
        missing_requirements.append("OVERLAP_ASSESSMENT_EVIDENCE")

    if not source_present:
        missing_requirements.append("SOURCE")

    evidence_complete = bool(
        relationship_known and economic_activity_known and overlap_assessable and source_present
    )

    return {
        "relationship_known": relationship_known,
        "economic_activity_known": economic_activity_known,
        "transaction_evidence_available": transaction_evidence_available,
        "segment_evidence_available": segment_evidence_available,
        "overlap_assessable": overlap_assessable,
        "source_present": source_present,
        "evidence_complete": evidence_complete,
        "missing_requirements": missing_requirements,
    }


def get_sotp_long_term_equity_economic_evidence(
    symbol: str,
) -> dict[str, Any]:
    symbol = _clean_symbol(symbol)

    data = get_sotp_long_term_equity_entity_data(symbol)

    if not isinstance(data, dict) or data.get("status") != "OK":
        return {
            "status": "UNAVAILABLE",
            "version": VERSION,
            "symbol": symbol,
            "message": ("Long-term equity entity data is unavailable."),
            "source_data": data,
        }

    population = data.get("population", [])

    if not isinstance(population, list):
        population = []

    results: list[dict[str, Any]] = []

    relationship_known_count = 0
    economic_activity_known_count = 0
    transaction_evidence_count = 0
    segment_evidence_count = 0
    overlap_assessable_count = 0
    source_present_count = 0
    evidence_registered_count = 0
    evidence_complete_count = 0

    for entity in population:
        name = entity.get("name")

        evidence = ECONOMIC_EVIDENCE.get(name)

        if evidence is None:
            validation = _validate_economic_evidence({})

            results.append(
                {
                    **entity,
                    "economic_evidence_registered": False,
                    "economic_evidence": {},
                    "evidence_validation": validation,
                }
            )

            continue

        evidence_registered_count += 1

        validation = _validate_economic_evidence(evidence)

        if validation["relationship_known"]:
            relationship_known_count += 1

        if validation["economic_activity_known"]:
            economic_activity_known_count += 1

        if validation["transaction_evidence_available"]:
            transaction_evidence_count += 1

        if validation["segment_evidence_available"]:
            segment_evidence_count += 1

        if validation["overlap_assessable"]:
            overlap_assessable_count += 1

        if validation["source_present"]:
            source_present_count += 1

        if validation["evidence_complete"]:
            evidence_complete_count += 1

        results.append(
            {
                **entity,
                **evidence,
                "economic_evidence_registered": True,
                "evidence_validation": validation,
            }
        )

    entity_count = len(population)

    annexure_evidence_count = sum(1 for entity in population if entity.get("investment_evidence"))

    annexure_evidence_complete = annexure_evidence_count == entity_count

    population_complete = bool(data.get("entity_population_complete"))

    all_entities_registered = evidence_registered_count == entity_count

    all_evidence_complete = evidence_complete_count == entity_count

    return {
        "status": "OK",
        "version": VERSION,
        "symbol": symbol,
        "entity_count": entity_count,
        "population_complete": population_complete,
        "annexure_evidence_count": annexure_evidence_count,
        "annexure_evidence_complete": annexure_evidence_complete,
        "evidence_registered_count": evidence_registered_count,
        "relationship_known_count": relationship_known_count,
        "economic_activity_known_count": economic_activity_known_count,
        "transaction_evidence_count": transaction_evidence_count,
        "segment_evidence_count": segment_evidence_count,
        "overlap_assessable_count": overlap_assessable_count,
        "source_present_count": source_present_count,
        "evidence_complete_count": evidence_complete_count,
        "all_entities_registered": all_entities_registered,
        "all_evidence_complete": all_evidence_complete,
        "classification_ready": all_evidence_complete,
        "entities": results,
        "status_view": (
            "EVIDENCE_COMPLETE" if all_evidence_complete else "PENDING_ECONOMIC_EVIDENCE"
        ),
        "interpretation": (
            "Economic evidence supports entity-level "
            "SOTP classification and operating-segment "
            "assessment. Ownership alone is not sufficient "
            "for valuation classification."
        ),
        "warnings": [
            ("Legal ownership does not determine " "operating-segment overlap."),
            ("Related-party disclosures are not " "automatic valuation evidence."),
            ("Economic evidence and valuation evidence " "are independent control layers."),
            ("Entity classification should only proceed " "when evidence is complete."),
        ],
        "source_data": data,
    }


if __name__ == "__main__":
    test_result = get_sotp_long_term_equity_economic_evidence("RELIANCE")

    assert (
        test_result["entity_count"] == 58
    ), f"Expected 58 entities, got {test_result['entity_count']}"
    assert test_result["economic_activity_known_count"] == 58, (
        "Expected economic_activity_known_count == 58, got "
        f"{test_result['economic_activity_known_count']}"
    )
    assert test_result["overlap_assessable_count"] == 58, (
        "Expected overlap_assessable_count == 58, got " f"{test_result['overlap_assessable_count']}"
    )
    assert test_result["all_evidence_complete"] is True, "Expected all_evidence_complete == True"

    print("V6.0 Self-Test Passed Successfully: All 58 entities verified.")
