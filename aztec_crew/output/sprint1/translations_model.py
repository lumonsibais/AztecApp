```python
from app.extensions import db
from datetime import datetime

class Translation(db.Model):
    __tablename__ = 'translations'
    id = db.String(36), primary_key=True
    entity_type = db.String(50), nullable=False
    entity_id = db.String(36), nullable=False
    locale = db.String(5), nullable=False
    field = db.String(50), nullable=False
    value = db.Text, nullable=False
    created_at = db.DateTime, default=datetime.utcnow
    updated_at = db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow

    __table_args__ = (
        db.UniqueConstraint('entity_type', 'entity_id', 'locale', 'field', name='uq_translation'),
        db.Index('ix_translation_lookup', 'entity_type', 'entity_id', 'locale'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'entityType': self.entity_type,
            'entityId': self.entity_id,
            'locale': self.locale,
            'field': self.field,
            'value': self.value,
        }
```