// Published names and access rules only. No scene is fetched from this module.
// Collection identifiers were read from the Bhoonidhi API specification on 5 Nov 2026.
// https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/

export const CATALOGUE_AS_OF = '2026-11-05';
export const API_DOCS = 'https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/';
export const BHOONIDHI_HOME = 'https://bhoonidhi.nrsc.gov.in/bhoonidhi/home.html';

export const PUBLISHED_COLLECTION_IDS = [
  'ResourceSat-2_AWIFS_L2', 'ResourceSat-2_AWIFS_BOA', 'ResourceSat-2_LISS3_L2', 'ResourceSat-2_LISS3_BOA', 'ResourceSat-2_LISS4-MX70_L2',
  'ResourceSat-2A_AWIFS_L2', 'ResourceSat-2A_AWIFS_BOA', 'ResourceSat-2A_LISS3_L2', 'ResourceSat-2A_LISS3_BOA', 'ResourceSat-2A_LISS4-MX70_L2',
  'EOS-04_SAR-MRS_L2A', 'EOS-04_SAR-MRS_L2B', 'EOS-04_SAR-MRS_SM', 'EOS-04_SAR-CRS_L2A', 'EOS-04_SAR-CRS_L2B', 'EOS-04_SAR-FRS1_L2A', 'EOS-04_SAR-FRS2_L2A', 'EOS-04_SAR-MRS_1deg-mosaic', 'EOS-04_SAR-MRS_WS-1deg-mosaic',
  'EOS-06_OCM-LAC_L1C', 'EOS-06_OCM-LAC_L2C-AOD', 'EOS-06_OCM-LAC_L2C-CHL', 'EOS-06_OCM-LAC_L2C-DA', 'EOS-06_OCM-LAC_L2C-NDVI', 'EOS-06_OCM-LAC_L2C-RRS', 'EOS-06_OCM-LAC_L2C-TSM', 'EOS-06_OCM-LAC_NDVI_8day_360m', 'EOS-06_OCM-LAC_AOD_8day_500m', 'EOS-06_OCM-LAC_TSM_8day_500m',
  'EOS-06_OCM-GAC_L1C', 'EOS-06_OCM-GAC_L2C-AOD', 'EOS-06_OCM-GAC_L2C-CHL', 'EOS-06_OCM-GAC_L2C-DA', 'EOS-06_OCM-GAC_L2C-NDVI', 'EOS-06_OCM-GAC_L2C-RRS', 'EOS-06_OCM-GAC_L2C-TSM', 'EOS-06_OCM-GAC_L2C-VF', 'EOS-06_OCM-GAC_NDVI_8day_1km', 'EOS-06_OCM-GAC_AOD_8day_4km', 'EOS-06_OCM-GAC_Chlorophyll_8day_4km', 'EOS-06_OCM-GAC_DA_8day_4km', 'EOS-06_OCM-GAC_TSM_8day_4km',
  'EOS-06_SCAT_1B', 'EOS-06_SCAT_2B', 'EOS-06_SCAT_3SH', 'EOS-06_SCAT_3SV', 'EOS-06_SCAT_3WW',
  'NISAR_SSAR_RSLC', 'NISAR_SSAR_GSLC', 'NISAR_SSAR_GCOV', 'NISAR_SSAR_RUNW', 'NISAR_SSAR_GUNW', 'NISAR_SSAR_RIFG', 'NISAR_SSAR_ROFF', 'NISAR_SSAR_GOFF',
  'IRS-1A_LISS-1_L2', 'IRS-1A_LISS-2_L2', 'Sentinel-1A_SAR-IW_SLC', 'Sentinel-1A_SAR-IW_GRD', 'Novasar-1_AIS', 'CartoSat-1_PAN_CartoDEM_30m',
];

export const QUESTIONS = [
  {id: 'all', label: 'All routes'},
  {id: 'crop', label: 'Crop and surface'},
  {id: 'radar', label: 'All-weather radar'},
  {id: 'water', label: 'Water and coast'},
  {id: 'planning', label: 'Urban and planning'},
  {id: 'access', label: 'Access and policy'},
];

export const RULES = [
  {
    title: 'IRS open-data line',
    text: 'NRSC states that IRS satellite data at 5 m resolution and coarser is open through Bhoonidhi. Data finer than 5 m is free for Indian government entities that submit a declaration, and priced for non-government entities.',
    href: 'https://www.nrsc.gov.in/nrscnew/assets/pdf/brochures/Bhoonidhi_Brochure_2025.pdf',
    link: 'Bhoonidhi brochure, 2025',
  },
  {
    title: 'Thematic products are separate',
    text: 'Vegetation and water indices, land-use and land-cover, forest cover, and digital elevation models finer than 30 m are charged to non-government entities. A free scene and a derived map do not share a price.',
    href: 'https://www.nrsc.gov.in/nrscnew/assets/pdf/brochures/Bhoonidhi_Brochure_2025.pdf',
    link: 'Same brochure',
  },
  {
    title: 'IN-SPACe dissemination line',
    text: 'Indian Space Policy 2023 requires IN-SPACe authorisation to disseminate satellite remote-sensing data at a ground sampling distance of 30 cm or finer. Data coarser than 30 cm needs intimation. IN-SPACe is not a scene archive, and an organisation profile is not an imagery licence.',
    href: 'https://www.nrsc.gov.in/nrscnew/assets/pdf/Indian%20Space%20Policy%202023.pdf',
    link: 'Indian Space Policy 2023',
  },
];

const collection = (id, name, questions, note) => ({
  id, name, kind: 'collection', questions, note, scenesLoaded: false,
  provider: 'Bhoonidhi / NRSC', access: 'API token required. Not loaded here.', href: API_DOCS,
});
const route = (id, name, questions, note, href, provider) => ({
  id, name, kind: 'route', questions, note, scenesLoaded: false,
  provider, access: 'Open the official page. Nothing is copied into this workspace.', href,
});

export const FEATURED = [
  collection('ResourceSat-2A_AWIFS_L2', 'Resourcesat-2A AWiFS, Level-2', ['crop', 'planning'], 'Wide-swath optical collection named on the Bhoonidhi API page. Confirm the scene ground sampling distance against the 5 m open-data rule before reuse.'),
  collection('ResourceSat-2A_LISS3_L2', 'Resourcesat-2A LISS-III, Level-2', ['crop', 'planning'], 'Optical collection on the same API list. It is a different product from AWiFS and from the NOAA vegetation reading already shown beside district evidence.'),
  collection('ResourceSat-2A_LISS4-MX70_L2', 'Resourcesat-2A LISS-IV MX, Level-2', ['planning'], 'Finer optical collection on the API list. SAC describes Resourcesat-2/2A LISS-IV at 5.8 m for urban built-up mapping. Confirm whether a particular file is open imagery or a priced thematic product.'),
  collection('IRS-1A_LISS-1_L2', 'IRS-1A LISS-I, Level-2', ['planning'], 'The Bhoonidhi home page says historical IRS-1A ortho products from 1988 onwards are available for direct download. This is the matching collection identifier on the API list.'),
  collection('CartoSat-1_PAN_CartoDEM_30m', 'CartoDEM, 30 m', ['planning'], 'The collection identifier includes 30 m. NRSC prices elevation models finer than 30 m for non-government entities, so the scene record still has to be checked.'),
  collection('EOS-04_SAR-MRS_L2B', 'EOS-04 SAR medium-resolution, Level-2B', ['radar', 'crop'], 'The home page names an EOS-04 Level-2B terrain-normalised analysis-ready product. Radar can show the surface when an optical image is cloudy. It does not measure water depth or damage.'),
  collection('EOS-04_SAR-MRS_1deg-mosaic', 'EOS-04 SAR India mosaic, 1 degree tiles', ['radar'], 'The home page names an EOS-04 CEOS analysis-ready India mosaic as 1 degree tiles. A mosaic is a composed product, not a single acquisition.'),
  collection('Sentinel-1A_SAR-IW_GRD', 'Sentinel-1A interferometric wide, GRD', ['radar'], 'Named on the API collection list. The home page also offers Sentinel-1 and Sentinel-2 through browse and order.'),
  collection('NISAR_SSAR_GCOV', 'NISAR S-band geocoded covariance', ['radar'], 'Daily processed NISAR S-SAR collections are released from 8 July 2026. The product page says they are published about 48 hours after acquisition, once the accurate orbit is available. The home page dates the launch at 30 July 2025.'),
  collection('EOS-06_OCM-LAC_NDVI_8day_360m', 'EOS-06 ocean colour NDVI, 8 day, 360 m', ['crop'], 'The identifier includes the 8-day composite and 360 m. This is an Indian ocean-colour vegetation index. It does not replace, and is not dated with, the NOAA vegetation-health series.'),
  collection('EOS-06_OCM-GAC_NDVI_8day_1km', 'EOS-06 ocean colour NDVI, 8 day, 1 km', ['crop'], 'Coarser companion to the 360 m composite. The identifier includes 1 km. Use it as context for a large area, not for a parcel.'),
  collection('EOS-06_OCM-LAC_L2C-CHL', 'EOS-06 ocean colour chlorophyll', ['water'], 'Chlorophyll collection on the API list. It describes water, not a crop yield or a land price.'),
  collection('EOS-06_OCM-LAC_L2C-TSM', 'EOS-06 total suspended matter', ['water'], 'Suspended-matter collection on the API list, with an 8-day 500 m companion also published. It is not a flood extent.'),
  route('browse-order', 'Browse and order', ['access', 'crop', 'radar', 'planning'], 'The home page offers search, view, and download or order for open and priced IRS missions, Landsat-8, Sentinel-1 and Sentinel-2, NovaSAR, and NISAR S-SAR daily collections from 8 July 2026.', BHOONIDHI_HOME, 'Bhoonidhi / NRSC'),
  route('landsat-sentinel2', 'Landsat 8 and 9, Sentinel-2', ['crop', 'planning', 'access'], 'Named on the home page for regional distribution and browse and order. The API collection table reviewed on 5 Nov 2026 does not publish their collection identifiers, so none are invented here.', BHOONIDHI_HOME, 'Bhoonidhi / NRSC'),
  route('vista', 'Bhoonidhi Vista', ['radar', 'access'], 'The home page describes Vista as a view of daily acquisitions and temporal mosaics, including NISAR data over India. It is a viewer, not a file in this workspace.', BHOONIDHI_HOME, 'Bhoonidhi / NRSC'),
  route('upagrah', 'Upagrah orbit viewer', ['access'], 'The home page describes Upagrah as live satellite and orbit tracking at a chosen UTC time. Orbits are not scene measurements.', BHOONIDHI_HOME, 'Bhoonidhi / NRSC'),
  route('planner', 'PLANNeR for EOS-04', ['radar', 'access'], 'The home page says PLANNeR looks up possible future EOS-04 acquisition dates and accepts requests for fresh acquisitions. A possible date is not an acquired scene.', BHOONIDHI_HOME, 'Bhoonidhi / NRSC'),
  route('api-access', 'Bhoonidhi API', ['access'], 'STAC search and open-data download need a bearer token. The specification example expires in 1,200 seconds. Ask bhoonidhi@nrsc.gov.in to enable access. The private RealAssets module can search only after that token is in the service environment.', API_DOCS, 'Bhoonidhi / NRSC'),
  route('nisar-products', 'NISAR S-SAR product list', ['radar', 'access'], 'Standard, interferometric, and offset products are listed by NRSC, including range-Doppler SLC, geocoded SLC, covariance, unwrapped interferogram, and pixel offsets. Listing a product is not a download.', 'https://bhoonidhi.nrsc.gov.in/NISAR/NisarProducts.html', 'Bhoonidhi / NRSC'),
  route('vedas-builtup', 'VEDAS built-up layer, 500 AMRUT cities', ['planning'], 'SAC says this layer was extracted with a neural network from Resourcesat-2 LISS-IV for 2023-2024, at the 5.8 m resolution it states, for 500 cities named under AMRUT. It is a derived urban map on VEDAS. It is not loaded here, and a derived product can be priced even when a coarser scene is open.', 'https://vedas.sac.gov.in/', 'SAC / ISRO, VEDAS'),
  route('vedas-api', 'VEDAS API Centre', ['crop', 'planning', 'access'], 'A SAC and IN-SPACe industry webinar describes indices such as NDVI, EVI, NDWI, and NBR, plus composites for AWiFS and Sentinel-2. Registration and a key are required. IN-SPACe hosted the introduction. SAC operates the API.', 'https://vedas.sac.gov.in/', 'SAC / ISRO, introduced with IN-SPACe'),
  route('bhuvan-view', 'Bhuvan viewing layers', ['planning'], 'The public Bhuvan map exposes satellite imagery, administrative boundaries from state to cadastral, hydrology, roads, and rail as viewing layers. A cadastral view is not a title search. IN-SPACe workshop material discusses Bhuvan thematic maps as a platform opportunity. Those maps are not connected here.', 'https://bhuvan.nrsc.gov.in/', 'NRSC Bhuvan'),
  route('indus', 'INDUS interferometry software', ['radar', 'access'], 'SAC offers INDUS for EOS-04 interferometry, including a deformation map, a relative elevation map, and a coherence map. It is downloadable software with its own manual. Running it is a separate lab step, not a result in this case.', 'https://vedas.sac.gov.in/', 'SAC / ISRO'),
  route('inspace-rules', 'IN-SPACe authorisation', ['access', 'planning'], 'Use IN-SPACe for the dissemination rule and for facilitation. The public site does not provide a scene search. High-resolution dissemination over Indian territory is an authorisation, and coarser dissemination is an intimation. LiquiLens has a saved organisation profile and no imagery licence.', 'https://www.inspace.gov.in/', 'IN-SPACe'),
];

export function entriesFor(question) {
  if (!QUESTIONS.some(item => item.id === question)) throw new Error('Unknown catalogue question.');
  return question === 'all' ? FEATURED : FEATURED.filter(item => item.questions.includes(question));
}

function day(value, today) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('Use YYYY-MM-DD dates for a search draft.');
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== value) throw new Error('Use YYYY-MM-DD dates for a search draft.');
  if (value > today) throw new Error('A search draft cannot use a future date.');
  return value;
}

export function searchDraft({collectionId, bbox, start, end}, today) {
  if (!PUBLISHED_COLLECTION_IDS.includes(collectionId)) throw new Error('That collection is not on the reviewed Bhoonidhi API list.');
  if (!Array.isArray(bbox) || bbox.length !== 4 || bbox.some(value => typeof value !== 'number' || !Number.isFinite(value))) throw new Error('This district has no published extent for a search draft.');
  const [west, south, east, north] = bbox;
  if (!(west < east && south < north && west >= -180 && east <= 180 && south >= -90 && north <= 90)) throw new Error('District extent is not a usable west, south, east, north box.');
  const clock = day(today, today);
  const startDate = day(start, clock);
  const endDate = day(end, clock);
  if (startDate > endDate) throw new Error('The earlier image date must come first.');
  return {
    bbox: [west, south, east, north],
    start_date: startDate,
    end_date: endDate,
    collections: [collectionId],
    limit: 10,
  };
}
