import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { product } from './test/fixtures'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('product page', () => {
  beforeEach(() => {
    vi.stubGlobal('crypto', { randomUUID: () => 'test-key' })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('prevents a duplicate add while the first request is in progress', async () => {
    let finishAdd: ((response: Response) => void) | undefined
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const path = String(input)
      if (path.includes('/api/products/')) return Promise.resolve(jsonResponse(product))
      if (path === '/api/cart') return Promise.resolve(jsonResponse({ items: [], total_item_count: 0, subtotal_cents: 0 }))
      return new Promise<Response>((resolve) => { finishAdd = resolve })
    })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()

    render(<App />)
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('button', { name: 'Graphite' }))
    await user.click(screen.getByRole('button', { name: 'Medium' }))
    const addButton = screen.getByRole('button', { name: 'Add to cart' })
    await user.dblClick(addButton)

    expect(fetchMock.mock.calls.filter(([path]) => String(path) === '/api/cart/items')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Adding...' })).toBeDisabled()

    finishAdd?.(jsonResponse({ sku_id: 'g-m', added_quantity: 1, available_quantity: 1, cart_total_item_count: 1 }, 201))
    await screen.findByText('1 item added to your cart.')
  })

  it('clamps quantity when a newly selected SKU has less stock', async () => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const path = String(input)
      if (path.includes('/api/products/')) return Promise.resolve(jsonResponse(product))
      return Promise.resolve(jsonResponse({ items: [], total_item_count: 0, subtotal_cents: 0 }))
    }))
    const user = userEvent.setup()

    render(<App />)
    await screen.findByRole('heading', { name: product.name })
    await user.click(screen.getByRole('button', { name: 'Graphite' }))
    await user.click(screen.getByRole('button', { name: 'Small' }))
    await user.click(screen.getByRole('button', { name: 'Increase quantity' }))
    await user.click(screen.getByRole('button', { name: 'Increase quantity' }))
    expect(screen.getByLabelText('Quantity')).toHaveTextContent('3')

    await user.click(screen.getByRole('button', { name: 'Signal Red' }))
    await user.click(screen.getByRole('button', { name: 'Medium' }))
    await waitFor(() => expect(screen.getByLabelText('Quantity')).toHaveTextContent('1'))
  })
})
