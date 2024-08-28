from pathlib import Path
from typing import Annotated

import typer
from rich import pretty

from semdoc.reader import load_path
from semdoc.analyzer import Sequential, TreeOrganizer, Logicalizer, Tablelizer
from semdoc.analyzer import surya
from semdoc.analyzer.tidier import HeadingLevelTidier, NonBlockWrapper
from semdoc.gui import show_boxes
from semdoc.writer import get_writer


def main(
    input: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Input document",
        ),
    ],
    output: Annotated[
        Path,
        typer.Argument(
            dir_okay=False,
            writable=True,
            help="Output document",
        ),
    ],
    print_result: Annotated[
        bool,
        typer.Option(help="Pretty print the semantic tree of the document"),
    ] = False,
    visualize_result: Annotated[
        bool, typer.Option(help="Show the document annotated with detected boxes")
    ] = False,
):
    doc = load_path(input)
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
    tablelizer = Tablelizer()
    logical_pipeline.add(tablelizer)
    logicalizer = Logicalizer()
    logical_pipeline.add(logicalizer)
    heading_level_tidier = HeadingLevelTidier()
    logical_pipeline.add(heading_level_tidier)
    non_block_wrapper = NonBlockWrapper()
    logical_pipeline.add(non_block_wrapper)

    ocr_result = ocr_pipeline.run(physical)
    logical_result = logical_pipeline.run(ocr_result)

    format = output.suffix[1:]
    writer = get_writer(format)(logical_result)
    writer.write_file(output)
    if visualize_result:
        show_boxes(doc, logical_result)
    if print_result:
        pretty.pprint(logical_result.to_dict())


def run():
    typer.run(main)
