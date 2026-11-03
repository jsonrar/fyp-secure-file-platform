// @vitest-environment node
// Exercise the locked Node dependency over loopback, without real credentials.
import { createServer, type IncomingHttpHeaders, type Server } from 'node:http'
import { createRequire } from 'node:module'
import { runInNewContext } from 'node:vm'
import { describe, expect, it } from 'vitest'

const redirects = createRequire(import.meta.url)('follow-redirects')

async function listen(server: Server): Promise<number> {
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('Missing loopback port')
  return address.port
}

async function close(server: Server): Promise<void> {
  server.closeAllConnections()
  await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
}

describe('locked redirect transport credential stripping', () => {
  it.each(['local', 'cross-realm'])('removes a sensitive header for %s arrays', async realm => {
    let received: IncomingHttpHeaders = {}
    const target = createServer((req, res) => {
      received = req.headers
      res.end('ok')
    })
    const targetPort = await listen(target)
    const source = createServer((_req, res) => {
      res.writeHead(302, { Location: `http://127.0.0.1:${targetPort}/target` })
      res.end()
    })
    try {
      const sourcePort = await listen(source)
      const sensitiveHeaders = realm === 'cross-realm'
        ? runInNewContext("['X-Synthetic-Credential']")
        : ['X-Synthetic-Credential']
      await new Promise<void>((resolve, reject) => {
        const request = redirects.http.get({
          hostname: '127.0.0.1', port: sourcePort, path: '/', sensitiveHeaders,
          headers: { 'X-Synthetic-Credential': 'test-only-value', 'X-Harmless': 'retained' }
        }, (response: import('node:http').IncomingMessage) => {
          response.resume()
          response.on('end', resolve)
          response.on('error', reject)
        })
        request.on('error', reject)
        request.setTimeout(2000, () => request.destroy(new Error('Loopback request timed out')))
      })
      expect(received['x-synthetic-credential']).toBeUndefined()
      expect(received['x-harmless']).toBe('retained')
    } finally {
      await Promise.all([close(source), close(target)])
    }
  })
})
