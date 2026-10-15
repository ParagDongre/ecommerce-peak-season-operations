"""Build docs/*.md and README.md from the pipeline outputs. Run after `python -m src.run_pipeline`."""
from __future__ import annotations

from . import docs_a, docs_b
from .docs_common import DOCS, ROOT, load


def main() -> list[str]:
    c = load()
    DOCS.mkdir(exist_ok=True)
    files = {
        DOCS / "01_Project_Charter.md": docs_a.charter(c),
        DOCS / "02_KPI_Dictionary.md": docs_a.kpi_dictionary(c),
        DOCS / "03_Operational_Analysis.md": docs_a.operational_analysis(c),
        DOCS / "05_Program_Status_Report.md": docs_a.status_report(c),
        DOCS / "07_Six_Sigma_DMAIC.md": docs_b.dmaic(c),
        DOCS / "08_Executive_Readout.md": docs_b.executive_readout(c),
        DOCS / "09_Methodology_and_Limitations.md": docs_b.methodology(c),
        DOCS / "10_Portfolio_Summary.md": docs_b.portfolio(c),
        ROOT / "README.md": docs_b.readme(c),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    return [str(p.relative_to(ROOT)) for p in files]


if __name__ == "__main__":
    for f in main():
        print("wrote", f)
