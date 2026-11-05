# Land and planning research workspace

This public workspace joins a **geographic context** with researcher-supplied
price and planning records. It does not include a connected property-price feed.

## Working with a case

1. Select a district from the verified 2021 geoBoundaries catalogue. The extent
   frames dated NASA GIBS Terra MODIS imagery; it does not establish the location
   or boundary of a particular property.
2. Enter a reviewed observation with its source, locator, observation date,
   retrieval timestamp, rights status, units and comparison basis. Reuse a source
   when appropriate. Records can be edited or removed and the last removal undone.
3. Add independently dated planning notes. These remain researcher-recorded
   references, not confirmation of title or development permission.
4. Optionally calculate a scenario using explicit assumptions. Changing an input
   clears the previous result until it is recalculated.
5. Download the complete case before leaving the page. Data stays in the tab;
   source URLs are not fetched, and no case is placed in browser storage.

## Files and interoperability

- **Research case JSON** uses `liquilens.land-research.v1` and contains the selected
  context, price evidence, planning records, assumptions, recalculated scenario
  results and interpretation limits.
- **Evidence JSON** uses `realassets.evidence.v1`. It is compatible with the
  RealAssets source/observation contract. This public view does not import lender
  or charge relationships.
- **CSV** contains observations with source identities and methodology. Keep the
  evidence JSON alongside it for the complete source register.
- **Printable brief** is a standalone HTML document. Open it and use the browser's
  Print command to save a PDF.

Imports are limited to 1 MiB. Full case imports resolve the district against the
verified catalogue and recompute scenarios from their inputs. They do not trust
imported district descriptions or precomputed scenario outcomes.

## Evidence distinctions

Asking prices, registered sales, DLC/circle rates, reported valuations and housing
indices remain separate. A series may not mix places, bases, units or methodology.
Two comparable dated observations are needed before a change is calculated. A
housing index requires its base year and cannot value a parcel. Price conversion
supports square metres, square feet and square yards; local units are not guessed.

The scenario is arithmetic for a bullet loan with interest and carrying costs
paid from equity and principal repaid at exit. It does not model rent, tax,
construction draws, refinancing or legal costs, and it is not a valuation.

## Satellite and planning access

Displayed imagery is NASA GIBS. Bhoonidhi is linked as a separate Indian imagery
discovery/access route; no Bhoonidhi scenes are downloaded by this workspace.
IN-SPACe is a facilitation route, not a data feed. Official planning and property
portals are listed with their access state and interpretation limits.

The context URL contains only the district ID, imagery viewport and image dates.
It does not carry price records, source documents, planning notes or assumptions.
