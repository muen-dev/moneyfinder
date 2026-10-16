# New York unclaimed-funds data import

The application uses the demo corpus unless `NY_UNCLAIMED_DATA_FILE` is set.
That prevents synthetic records from being mistaken for government results.

## Supported TSV columns

```text
found_name	property_type	city	zip	amount	source
Example Foods	Uncashed vendor check	Brooklyn	11201	412.00	import:ny-export.tsv
```

Run the API with an imported file:

```bash
NY_UNCLAIMED_DATA_FILE=/absolute/path/ny-export.tsv \
PORT=4173 python3 -m src.server
```

The source label is returned on every match. Amounts may be blank because some
public/location-provider exports do not disclose amounts. Do not call imported
data “real-time” unless the file’s source and retrieval timestamp are stored.

The adapter is `src/search/imported.py`; a future official API adapter should
implement the same `UnclaimedSearchAdapter` protocol.
