```python
from geoalchemy2 import Geography
from app.extensions import db
from datetime import datetime

class LakeGeometry(db.Model):
    __tablename__ = 'lake_geometries'
    id = db.String(36), primary_key=True
    name = db.String(255), nullable=False
    geom = db.Column(Geography(geometry_type='POLYGON', srid=4326), nullable=False)
    year_estimate = db.Integer
    tenochtitlan_name = db.String(255)
    description = db.Text
    created_at = db.DateTime, default=datetime.utcnow

    __table_args__ = (
        db.Index('ix_lake_geometries_geom', 'geom', postgresql_using='gist'),
    )
```