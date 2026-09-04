"""A project's corpus as read: every plan and suggestion, live and archived."""

from datetime import datetime

from pydantic import BaseModel

from domain.document import Document, DocumentKind


class CorpusIndex(BaseModel):
    documents: list[Document]
    read_at: datetime

    def find(self, kind: DocumentKind, stem: str) -> Document | None:
        for document in self.documents:
            if document.kind == kind and document.stem == stem:
                return document
        return None

    def live(self) -> list[Document]:
        return [d for d in self.documents if not d.archived]

    def archived(self) -> list[Document]:
        return [d for d in self.documents if d.archived]


class CorpusSummary(BaseModel):
    live_plans: int
    live_suggestions: int
    archived: int
    watching: bool
    """The board has an ear on the corpus. False is shown, never hidden."""
    watch_note: str | None
    """Why it is not watching, when it is not."""
    read_at: datetime
