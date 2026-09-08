```python
from geoalchemy2 import Geography
from app.extensions import db

geom = db.Column(Geography(geometry_type='POINT', srid=4326), nullable=True)

__table_args__ = (
    db.Index('ix_places_geom', 'geom', postgresql_using='gist'),
)
```