/**
 * The measured results quoted on the home page and on the sign-in pages. One list, so the numbers
 * cannot drift apart; they come from our own test runs on the live site (see the project reports).
 */
export const proof = [
  { value: '0 / 5,094', label: 'downloads failed their integrity check' },
  { value: '102 / 102', label: 'uploads succeeded at 100 concurrent users on the live server' },
  { value: '0 FAIL', label: 'in an OWASP ZAP scan of this site' },
  { value: '500 MB', label: 'per file and round-tripped byte-exact in testing' },
]
