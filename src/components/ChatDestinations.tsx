import { Link } from 'react-router-dom';
import { ArrowUpRight, ArrowRight } from 'lucide-react';
import { resolveDestinations } from '../lib/chat-destinations';

export default function ChatDestinations({ ids, onNavigate }: { ids?: string[]; onNavigate: () => void }) {
  const destinations = resolveDestinations(ids);
  if (!destinations.length) return null;
  return <nav className="chat-destinations" aria-label="Explore destinations">
    {destinations.map(destination => destination.kind === 'internal'
      ? <Link key={destination.id} to={destination.href} state={{ chatNavigation: true }} onClick={event => {
          if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) onNavigate();
        }}><span>{destination.label}</span><ArrowRight size={17} aria-hidden="true" /></Link>
      : <a key={destination.id} href={destination.href} target="_blank" rel="noopener noreferrer"><span>{destination.label}<span className="sr-only"> (opens a new tab)</span></span><ArrowUpRight size={17} aria-hidden="true" /></a>)}
  </nav>;
}
