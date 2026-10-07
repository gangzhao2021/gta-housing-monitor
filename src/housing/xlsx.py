"""Minimal dependency-free .xlsx reader: {sheet name: {row number: {column letter: text}}}."""
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def read(path):
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            table = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(node.text or "" for node in item.iter("{%s}t" % NS["m"])) for item in table]
        result = {}
        for sheet in workbook.find("m:sheets", NS):
            target = targets[sheet.attrib["{%s}id" % NS["r"]]].lstrip("/")
            sheet_path = target if target.startswith("xl/") else posixpath.normpath(posixpath.join("xl", target))
            rows = {}
            for row in ET.fromstring(archive.read(sheet_path)).findall(".//m:sheetData/m:row", NS):
                values = {}
                for cell in row.findall("m:c", NS):
                    column = re.match(r"[A-Z]+", cell.attrib["r"]).group()
                    if cell.attrib.get("t") == "inlineStr":
                        values[column] = "".join(node.text or "" for node in cell.iter("{%s}t" % NS["m"]))
                        continue
                    value = cell.find("m:v", NS)
                    if value is not None:
                        values[column] = strings[int(value.text)] if cell.attrib.get("t") == "s" else value.text
                rows[int(row.attrib["r"])] = values
            result[sheet.attrib["name"]] = rows
    return result
