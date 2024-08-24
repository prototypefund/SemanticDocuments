from rich.pretty import pprint
from pathlib import Path
import xml.etree.ElementTree as ET
from rich import pretty

from semdoc import reader
from semdoc import analyzer
from semdoc.analyzer import surya, opencv, tesseract
from semdoc.analyzer import Sequential, TreeOrganizer, Logicalizer
from semdoc.writer import get_writer

import utils
from documents import simple_text


def test_bitmap_xml(tmp_path, simple_text):
    doc = reader.load_path(simple_text["path_png"])
    physical = doc.physical_structure()

    pipeline = analyzer.Sequential()
    segmentizer = opencv.Analyzer()
    pipeline.add(segmentizer)
    ocr = tesseract.Analyzer()
    pipeline.add(ocr)
    result = pipeline.run(physical)

    dest = tmp_path / Path("simple_text.xml")
    xml_output = get_writer("xml")(result)
    string = xml_output.tostring()
    xml_output.write_file(dest)

    result = ET.fromstring(dest.read_text())
    heading = result.findtext("./Page/Region[1]")
    assert heading == "Hello, world!"


def test_bitmap_pdf(tmp_path, simple_text):
    doc = reader.load_path(simple_text["path_png"])
    physical = doc.physical_structure()

    ocr_pipeline = Sequential()
    text_detector = surya.TextLines()
    ocr_pipeline.add(text_detector)
    text_recognizer = surya.OCR()
    ocr_pipeline.add(text_recognizer)
    layout_recognizer = surya.Layout()
    ocr_pipeline.add(layout_recognizer)

    logical_pipeline = Sequential()
    organizer = TreeOrganizer()
    logical_pipeline.add(organizer)
    logicalizer = Logicalizer()
    logical_pipeline.add(logicalizer)

    ocr_result = ocr_pipeline.run(physical)
    logical_result = logical_pipeline.run(ocr_result)

    dest = tmp_path / Path("simple_text.pdf")
    writer = get_writer("pdf")(logical_result)
    writer.write_file(dest)

    validation_results = utils.validate_verapdf(dest, flavour="ua1")
    pretty.pprint(validation_results)
    assert len(validation_results) == 0

    structure = utils.get_tag_structure(dest)
    headings = structure.findall("./Document/H1/MCID")
    assert len(headings) == 1
    utils.assert_similar(headings[0].text, "Hello, world!")
    paragraphs = structure.findall("./Document/P")
    assert len(paragraphs) == 2
    mcids = structure.findall(".//MCID")
    text_lines = list(map(lambda elem: elem.text, mcids))
    utils.assert_similar(text_lines, simple_text["text_lines"])

    mupdf = utils.mupdf_open(dest)
    assert mupdf.page_count == 1
