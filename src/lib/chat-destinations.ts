import catalog from '../../data/chat_destinations.json';

export interface Destination { id: string; label: string; kind: 'internal' | 'external'; href: string; subject: string }
const internalRoutes = new Set(['/photography', '/photography#authors-choice', '/videos', '/essays', '/hobbies']);
const externalHosts = new Set(['www.youtube.com', 'open.spotify.com', 'www.realmadrid.com']);
export function validDestination(entry: Destination): boolean {
  if (entry.kind === 'internal') return internalRoutes.has(entry.href);
  try {
    const url = new URL(entry.href);
    return entry.kind === 'external' && url.protocol === 'https:' && !url.username && !url.password && externalHosts.has(url.hostname) && !url.port;
  } catch { return false; }
}
export function resolveDestinations(ids: string[] = []): Destination[] {
  return [...new Set(ids)].flatMap(id => {
    const entry = catalog.find(entry => entry.id === id) as Destination | undefined;
    return entry && validDestination(entry) ? [entry] : [];
  }).slice(0, 6);
}
