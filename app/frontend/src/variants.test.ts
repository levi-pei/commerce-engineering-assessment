import { describe, expect, it } from 'vitest'

import { product } from './test/fixtures'
import { isOptionSelectable, resolveSku } from './variants'

describe('variant resolution', () => {
  it('resolves only a complete exact option combination', () => {
    expect(resolveSku(product, { colour: 'Signal Red' })).toBeNull()
    expect(resolveSku(product, { colour: 'Signal Red', size: 'Medium' })?.id).toBe('r-m')
    expect(resolveSku(product, { colour: 'Signal Red', size: 'XL' })).toBeNull()
  })

  it('disables impossible and unavailable combinations but preserves out-of-stock states', () => {
    expect(isOptionSelectable(product, { colour: 'Signal Red' }, 'size', 'XL')).toBe(false)
    expect(isOptionSelectable(product, { colour: 'Graphite' }, 'size', 'XL')).toBe(false)
    expect(isOptionSelectable(product, { colour: 'Graphite' }, 'size', 'Large')).toBe(true)
  })
})

