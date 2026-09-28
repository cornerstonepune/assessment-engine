"""What a person's check teaches the reader (goals/s19-validation-teaches.yaml): the pixels it read. Each answer's
crop — its run of boxes as photographed, exactly what the digit reader was handed (`boxes.photo`) — is kept beside the
scans when it is read, and its reading records where; the label is what a person later says the child wrote
(`answer_checked`). Together they are what a reader of this school's handwriting is trained and measured on (step 3).
Crops stay beside the scans, never in the database or the repository (rule 6).
"""

from pathlib import Path

from engine.w3_read import read_eval

CROPS = Path(read_eval.ASSESSMENTS).expanduser() / "crops"


def keeper(scan, page_no):
    """For one page of one scanned copy: (slot, png) → where the crop was kept, as a reading records a path (from
    the home folder, so it resolves on the server as on a Mac). The same answer read again is written in place."""
    folder = CROPS / Path(scan).stem

    def keep(slot, png):
        folder.mkdir(parents=True, exist_ok=True)
        kept = folder / f"p{page_no}-{slot}.png"
        kept.write_bytes(png)
        return str(kept.resolve()).replace(str(Path.home()), "~")

    return keep


def path(recorded):
    """A crop's recorded path as a file on this machine."""
    return Path(recorded).expanduser()
