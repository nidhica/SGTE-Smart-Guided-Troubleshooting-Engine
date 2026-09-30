/**
 * Quick-select category flows (Phase 77).
 *
 * Each default `query` must produce a grounded MOCK plan via existing SIIS
 * and/or catalogue short-circuits. Options are alternate verified queries —
 * never fabricated evidence.
 *
 * Keep in sync with tests/test_phase77_category_flows.py
 */

export type CategoryOption = {
  label: string
  query: string
}

export type CategoryFlow = {
  id: 'battery' | 'display' | 'touch' | 'connectivity'
  label: string
  /** Short line under the category title */
  example: string
  /** Default complaint inserted on category click */
  query: string
  /** Additional grounded problems for this category */
  options: CategoryOption[]
}

export const CATEGORY_FLOWS: CategoryFlow[] = [
  {
    id: 'battery',
    label: 'Battery & Charging',
    example: 'Turn off fast charging',
    // Catalogue short-circuit: Disable Fast charging → DL-0403 (Phase 66/72)
    query: 'How do I turn off fast charging?',
    options: [
      {
        label: 'Turn off fast charging',
        query: 'How do I turn off fast charging?',
      },
      {
        label: 'Turn on fast charging',
        query: 'How do I turn on fast charging?',
      },
    ],
  },
  {
    id: 'display',
    label: 'Display & Screen',
    example: 'Use Multi window',
    // SIIS row_7/12 Multi window + DL-0270 (Phase 66/72)
    query: 'How do I use Multi window on my Galaxy phone?',
    options: [
      {
        label: 'Use Multi window',
        query: 'How do I use Multi window on my Galaxy phone?',
      },
      {
        label: 'Screen is completely black',
        query: 'My phone screen is completely black.',
      },
    ],
  },
  {
    id: 'touch',
    label: 'Touch & Gestures',
    example: 'Screen not responding to touch',
    // SIIS row_21 touchscreen issues (working reference)
    query: 'My phone screen is not responding properly to touch.',
    options: [
      {
        label: 'Touch not responding',
        query: 'My phone screen is not responding properly to touch.',
      },
      {
        label: 'Increase touch sensitivity',
        query: 'How do I increase touch sensitivity?',
      },
    ],
  },
  {
    id: 'connectivity',
    label: 'Connectivity',
    example: 'Mirror screen to Samsung TV',
    // SIIS row_8 Screen mirroring — only connectivity-family SIIS in corpus
    // (generic Wi-Fi connect has no SIIS; do not invent a Wi-Fi plan)
    query: 'How do I mirror my phone screen to a Samsung TV?',
    options: [
      {
        label: 'Mirror to Samsung TV',
        query: 'How do I mirror my phone screen to a Samsung TV?',
      },
    ],
  },
]
