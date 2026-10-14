import type { Product } from '../types'

export const product: Product = {
  id: 'everyday-shell',
  name: 'Fieldwork Utility Shell',
  description: 'A weather-ready overshirt.',
  option_dimensions: [
    { name: 'colour', label: 'Colour', values: ['Graphite', 'Signal Red'] },
    { name: 'size', label: 'Size', values: ['Small', 'Medium', 'Large', 'XL'] },
  ],
  skus: [
    { id: 'g-s', price_cents: 12900, available_quantity: 5, is_available: true, image_url: '/g.png', options: { colour: 'Graphite', size: 'Small' } },
    { id: 'g-m', price_cents: 12900, available_quantity: 2, is_available: true, image_url: '/g.png', options: { colour: 'Graphite', size: 'Medium' } },
    { id: 'g-l', price_cents: 12900, available_quantity: 0, is_available: true, image_url: '/g.png', options: { colour: 'Graphite', size: 'Large' } },
    { id: 'g-xl', price_cents: 12900, available_quantity: 3, is_available: false, image_url: '/g.png', options: { colour: 'Graphite', size: 'XL' } },
    { id: 'r-s', price_cents: 13400, available_quantity: 4, is_available: true, image_url: '/r.png', options: { colour: 'Signal Red', size: 'Small' } },
    { id: 'r-m', price_cents: 13400, available_quantity: 1, is_available: true, image_url: '/r.png', options: { colour: 'Signal Red', size: 'Medium' } },
  ],
}

