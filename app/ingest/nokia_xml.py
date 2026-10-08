import gzip
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

class NokiaXMLParser:
    """
    Streaming 3GPP PM XML (TS 32.435) parser for Nokia CMG / UPF performance measurement files.
    Extracts measObjLdn, measInfoId, counters, suspect flags, and timestamps.
    """
    def __init__(self, xml_path: Path):
        self.xml_path = Path(xml_path)

    def parse() -> List[Dict[str, Any]]:
        records = []
        if not self.xml_path.exists():
            return records

        open_fn = gzip.open if self.xml_path.suffix == '.gz' else open
        
        try:
            with open_fn(self.xml_path, 'rt', encoding='utf-8', errors='ignore') as f:
                # Fast streaming parse with iterparse
                context = ET.iterparse(f, events=('start', 'end'))
                context = iter(context)
                event, root = next(context)
                
                ns = {'m': 'http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec'}
                
                begin_time = None
                end_time = None
                
                # First pass to find beginTime and managedElement
                for event, elem in context:
                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    
                    if tag_name == 'fileHeader':
                        for child in elem:
                            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            if child_tag == 'measCollec':
                                begin_time = child.attrib.get('beginTime')
                    elif tag_name == 'fileFooter':
                        for child in elem:
                            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            if child_tag == 'measCollec':
                                end_time = child.attrib.get('endTime')
                    elif tag_name == 'measInfo':
                        meas_info_id = elem.attrib.get('measInfoId')
                        meas_types = []
                        for child in elem:
                            c_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            if c_tag == 'measTypes' or c_tag == 'measType':
                                meas_types = child.text.strip().split() if child.text else []
                            elif c_tag == 'measValue':
                                meas_obj_ldn = child.attrib.get('measObjLdn', '')
                                suspect_node = child.find('.//{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}suspect')
                                is_suspect = (suspect_node is not None and suspect_node.text == 'true')
                                
                                results = [r.text for r in child.findall('.//{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}r')]
                                
                                for idx, val in enumerate(results):
                                    if idx < len(meas_types):
                                        kpi_name = meas_types[idx]
                                        try:
                                            num_val = float(val) if val is not None else 0.0
                                        except ValueError:
                                            num_val = 0.0
                                            
                                        records.append({
                                            "timestamp": begin_time or datetime.utcnow().isoformat(),
                                            "meas_info_id": meas_info_id,
                                            "meas_obj_ldn": meas_obj_ldn,
                                            "kpi_name": kpi_name,
                                            "value": num_val,
                                            "suspect": is_suspect
                                        })
                        elem.clear()  # Clear element from memory
        except Exception as e:
            print(f"Error parsing Nokia XML {self.xml_path}: {e}")
            
        return records

def parse_all_nokia_xmls(directory: Path) -> pd.DataFrame:
    all_records = []
    xml_files = list(directory.glob("*.xml")) + list(directory.glob("*.xml.gz"))
    for f in xml_files:
        parser = NokiaXMLParser(f)
        all_records.extend(parser.parse())
    return pd.DataFrame(all_records)
