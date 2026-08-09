"""Import explicitly sourced maintainer verification records into a local dataset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from steam_graveyard.config import Settings
from steam_graveyard.database.repository import GameRepository
from steam_graveyard.models import ActivationMethod, ClaimStatus, Source
from steam_graveyard.services.exporter import DatasetExporter
from steam_graveyard.services.verifier import apply_maintainer_verification


class ImportRecord(BaseModel):
    appid: int
    claim_status: ClaimStatus
    verified_at: datetime
    method: str = Field(min_length=1)
    notes: str | None = None
    activation_method: ActivationMethod = ActivationMethod.NONE
    activation_id: str | None = None
    source: Source


def main() -> None:
    parser = argparse.ArgumentParser(description="Import source-backed claim verification records.")
    parser.add_argument("input", type=Path, help="JSON array of verification records")
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args()
    settings = Settings(data_dir=args.data_dir) if args.data_dir else Settings()
    repository = GameRepository(settings)
    repository.initialize()
    records = [
        ImportRecord.model_validate(item)
        for item in json.loads(args.input.read_text(encoding="utf-8"))
    ]
    for record in records:
        apply_maintainer_verification(
            repository,
            appid=record.appid,
            claim_status=record.claim_status,
            source=record.source,
            method=record.method,
            verified_at=record.verified_at,
            notes=record.notes,
            activation_method=record.activation_method,
            activation_id=record.activation_id,
        )
    DatasetExporter(repository, settings.export_dir).export_all()
    print(f"Imported {len(records)} verification record(s).")


if __name__ == "__main__":
    main()
