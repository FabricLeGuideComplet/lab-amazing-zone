import { useEffect, useState } from 'react';

import { useAuth } from '@/hooks/AuthContext';
import { getSanteEntrepots, type SanteEntrepot } from '@/services/entrepots';

const ENTREPOTS: Record<string, string> = {
  WH1: 'Saran (Orléans)',
  WH2: 'Saint-Quentin-Fallavier (Lyon)',
  WH3: 'Lesquin (Lille)',
  WH4: 'Vitrolles (Marseille)',
};

export function HomePage() {
  const { signOut, user } = useAuth();
  return (
    <div className="bg-gray-50 min-h-screen">
      <header className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Entrepôts en temps réel</h1>
          <p className="text-xs text-gray-500">Amazing Zone · activité des entrepôts d’après les événements du WMS</p>
        </div>
        <div className="flex items-center gap-4">
          {user?.email && <span className="text-sm text-gray-600">{user.email}</span>}
          <button onClick={() => void signOut()} className="text-gray-400 hover:text-gray-600 text-sm">
            Se déconnecter
          </button>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-6">
        <EntrepotsTempsReel />
      </main>
    </div>
  );
}

// Rien n'est poussé vers l'application : l'état des entrepôts est relu toutes les 30 secondes. La copie OneLake
// des événements, elle, n'avance que toutes les cinq minutes environ.
const ACTUALISATION_MS = 30_000;

function EntrepotsTempsReel() {
  const [sante, setSante] = useState<SanteEntrepot[]>([]);
  const [lu, setLu] = useState<Date | null>(null);
  const [erreur, setErreur] = useState('');

  useEffect(() => {
    let actif = true;
    const lire = async () => {
      try {
        const s = await getSanteEntrepots();
        if (!actif) return;
        setSante(s);
        setLu(new Date());
        setErreur('');
      } catch (e) {
        if (actif) setErreur(e instanceof Error ? e.message : String(e));
      }
    };
    void lire();
    const minuterie = window.setInterval(() => void lire(), ACTUALISATION_MS);
    return () => {
      actif = false;
      window.clearInterval(minuterie);
    };
  }, []);

  const derniereCopie = sante.find((s) => s.derniereCopie)?.derniereCopie ?? null;
  const retardCopie = derniereCopie && lu ? Math.max(0, Math.round((lu.getTime() - derniereCopie.getTime()) / 60_000)) : null;

  return (
    <section className="mb-6">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-700">Entrepôts en temps réel</h2>
        <span className="text-xs text-gray-400">
          Événements du WMS (copie OneLake de l’Eventhouse){lu ? ` · lu à ${lu.toLocaleTimeString('fr-FR')}` : ''}
          {retardCopie !== null ? ` · copie en retard de ${retardCopie} min` : ''}
        </span>
      </div>
      {erreur && <p className="mb-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{erreur}</p>}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {sante.map((s) => (
          <div
            key={s.codeEntrepot}
            className={`rounded-xl px-4 py-3 shadow-sm ${s.muet ? 'bg-red-50 ring-1 ring-red-300' : 'bg-white'}`}
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900">{s.codeEntrepot}</span>
              <span className={`text-xs font-medium ${s.muet ? 'text-red-700' : 'text-green-700'}`}>
                {s.muet ? 'Muet' : 'Actif'}
              </span>
            </div>
            <div className="text-xs text-gray-500">{ENTREPOTS[s.codeEntrepot] ?? ''}</div>
            <div className="mt-2 text-sm text-gray-700">
              {s.evenementsDerniereHeure} événements · {s.expeditionsDerniereHeure} expéditions en 1 h
            </div>
            <div className="text-xs text-gray-500">
              {s.dernierEvenement
                ? `Dernier événement il y a ${s.minutesSansEvenement} min`
                : 'Aucun événement reçu'}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
