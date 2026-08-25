# LiquiLens Postman collection

Import `liquilens-public-api.postman_collection.json` to exercise all eight
anonymous, read-only routes in the LiquiLens public OpenAPI contract. The
collection uses no secret, cookie, or bearer-token variable and defaults to the
production `https://api.liquilens.in` origin.

The repository artifact is live and versioned. A Postman public workspace or
API Network listing is **not** live: publication requires an owner-controlled
Postman account and manual review. Do not describe this file as a Postman
endorsement or directory listing.

The default institution slug is only an import-time example. Select a current
slug from the Failure Radar Board; an uncovered institution correctly returns
404 rather than receiving a synthetic score.
