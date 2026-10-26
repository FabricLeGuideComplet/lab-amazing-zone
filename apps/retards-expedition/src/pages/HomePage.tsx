import { useCallback, useEffect, useMemo, useState } from 'react';

import { useAuth } from '@/hooks/AuthContext';
import {
  LIBELLES_CAUSES,
  enregistrerCause,
  getCauses,
  getRetards,
  type Cause,
  type CauseSaisie,
  type Retard,
} from '@/services/retards';

const ENTREPOTS: Record<string, string> = {
  WH1: 'Saran (Orléans)',
  WH2: 'Saint-Quentin-Fallavier (Lyon)',
  WH3: 'Lesquin (Lille)',
  WH4: 'Marseille',
};

export function HomePage() {
  const { signOut, user } = useAuth();
  const [retards, setRetards] = useState<Retard[]>([]);
  const [causes, setCauses] = useState<Record<string, CauseSaisie>>({});
  const [entrepot, setEntrepot] = useState('');
  const [erreur, setErreur] = useState('');
  const [chargement, setChargement] = useState(true);

  const charger = useCallback(async () => {
    try {
      const [r, c] = await Promise.all([getRetards(), getCauses()]);
      setRetards(r);
      setCauses(Object.fromEntries(c.map((x) => [x.numeroCommande, x])));
      setErreur('');
    } catch (e) {
      setErreur(e instanceof Error ? e.message : String(e));
    } finally {
      setChargement(false);
    }
  }, []);

  useEffect(() => {
    void charger();
  }, [charger]);

  const visibles = useMemo(
    () => retards.filter((r) => !entrepot || r.codeEntrepot === entrepot),
    [retards, entrepot]
  );
  const renseignes = visibles.filter((r) => causes[r.numeroCommande]).length;
  const repartition = useMemo(() => {
    const n: Partial<Record<Cause, number>> = {};
    for (const r of visibles) {
      const c = causes[r.numeroCommande]?.cause;
      if (c) n[c] = (n[c] ?? 0) + 1;
    }
    return Object.entries(n).sort((a, b) => b[1] - a[1]);
  }, [visibles, causes]);

  return (
    <div className="bg-gray-50 min-h-screen">
      <header className="flex items-center justify-between px-8 py-4 bg-white border-b border-gray-200">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Retards d’expédition</h1>
          <p className="text-xs text-gray-500">Amazing Zone · commandes expédiées au-delà de 24 heures, 14 derniers jours</p>
        </div>
        <div className="flex items-center gap-4">
          {user?.email && <span className="text-sm text-gray-600">{user.email}</span>}
          <button onClick={() => void signOut()} className="text-gray-400 hover:text-gray-600 text-sm">
            Se déconnecter
          </button>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex flex-wrap items-end gap-4 mb-6">
          <label className="text-sm text-gray-700">
            Entrepôt
            <select
              value={entrepot}
              onChange={(e) => setEntrepot(e.target.value)}
              className="ml-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">Tous</option>
              {Object.entries(ENTREPOTS).map(([code, nom]) => (
                <option key={code} value={code}>
                  {code} · {nom}
                </option>
              ))}
            </select>
          </label>
          <Carte titre="Expéditions en retard" valeur={String(visibles.length)} />
          <Carte titre="Causes renseignées" valeur={`${renseignes} / ${visibles.length}`} />
          <Carte
            titre="Première cause"
            valeur={repartition[0] ? `${LIBELLES_CAUSES[repartition[0][0] as Cause]} (${repartition[0][1]})` : '—'}
          />
        </div>

        {erreur && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{erreur}</p>}
        {chargement ? (
          <p className="text-sm text-gray-400">Chargement…</p>
        ) : (
          <table className="w-full bg-white rounded-xl shadow-sm text-sm">
            <thead className="text-left text-xs uppercase text-gray-500 border-b">
              <tr>
                <th className="p-3">Commande</th>
                <th className="p-3">Entrepôt</th>
                <th className="p-3">Transporteur</th>
                <th className="p-3">Expédiée le</th>
                <th className="p-3 text-right">Délai (h)</th>
                <th className="p-3">Cause du retard</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((r) => (
                <Ligne key={r.numeroCommande} retard={r} saisie={causes[r.numeroCommande]} onSaved={charger} />
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  );
}

function Carte({ titre, valeur }: { titre: string; valeur: string }) {
  return (
    <div className="rounded-xl bg-white px-4 py-2 shadow-sm">
      <div className="text-xs text-gray-500">{titre}</div>
      <div className="text-lg font-semibold text-gray-900">{valeur}</div>
    </div>
  );
}

function Ligne({ retard, saisie, onSaved }: { retard: Retard; saisie?: CauseSaisie; onSaved: () => Promise<void> }) {
  const [cause, setCause] = useState<Cause | ''>(saisie?.cause ?? '');
  const [commentaire, setCommentaire] = useState(saisie?.commentaire ?? '');
  const [envoi, setEnvoi] = useState(false);

  const enregistrer = async () => {
    if (!cause) return;
    setEnvoi(true);
    try {
      await enregistrerCause(retard, cause, commentaire, saisie);
      await onSaved();
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <tr className="border-b last:border-0 align-top">
      <td className="p-3 font-mono">{retard.numeroCommande}</td>
      <td className="p-3">{retard.codeEntrepot}</td>
      <td className="p-3">{retard.transporteur}</td>
      <td className="p-3">{retard.dateExpedition}</td>
      <td className="p-3 text-right">{retard.delaiHeures}</td>
      <td className="p-3">
        <div className="flex gap-2">
          <select
            value={cause}
            onChange={(e) => setCause(e.target.value as Cause)}
            className="rounded-lg border border-gray-300 px-2 py-1"
          >
            <option value="">À renseigner</option>
            {Object.entries(LIBELLES_CAUSES).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <input
            value={commentaire}
            onChange={(e) => setCommentaire(e.target.value)}
            maxLength={500}
            placeholder="Commentaire"
            className="flex-1 rounded-lg border border-gray-300 px-2 py-1"
          />
          <button
            onClick={() => void enregistrer()}
            disabled={!cause || envoi}
            className="rounded-lg bg-blue-600 px-3 py-1 text-white disabled:opacity-40"
          >
            {saisie ? 'Modifier' : 'Enregistrer'}
          </button>
        </div>
        {saisie && (
          <div className="mt-1 text-xs text-gray-400">
            Saisi par {saisie.saisiPar} le {new Date(saisie.saisiLe).toLocaleString('fr-FR')}
          </div>
        )}
      </td>
    </tr>
  );
}
