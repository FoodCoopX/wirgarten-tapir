import React, { useEffect, useState } from "react";
import { Check, Pencil, Plus, Trash, X } from "react-bootstrap-icons";
import { BakeryApi } from "../../../api-client";
import type { BreadGroup } from "../../../api-client/models";
import { useApi } from "../../../hooks/useApi";
import { handleRequestError } from "../../../utils/handleRequestError";
import "../../styles/bakery_styles.css";

interface GroupsCardProps {
  csrfToken: string;
  breadsVersion: number;
  onGroupsChanged: () => void;
}

export const GroupsCard: React.FC<GroupsCardProps> = ({
  csrfToken,
  breadsVersion,
  onGroupsChanged,
}) => {
  const bakeryApi = useApi(BakeryApi, csrfToken);
  const [groups, setGroups] = useState<BreadGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [newGroupName, setNewGroupName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  useEffect(() => {
    loadGroups();
  }, [breadsVersion]);

  const loadGroups = () => {
    setLoading(true);
    bakeryApi
      .bakeryBreadGroupsList()
      .then((data) => {
        setGroups(data);
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Laden der Gruppen");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;

    bakeryApi
      .bakeryBreadGroupsCreate({ breadGroupRequest: { name: newGroupName } })
      .then(() => {
        setNewGroupName("");
        loadGroups();
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Erstellen der Gruppe");
      });
  };

  const handleStartEdit = (group: BreadGroup) => {
    setEditingId(group.id!);
    setEditingName(group.name);
  };

  const handleSaveEdit = (id: string) => {
    if (!editingName.trim()) return;

    bakeryApi
      .bakeryBreadGroupsPartialUpdate({
        id,
        patchedBreadGroupRequest: { name: editingName },
      })
      .then(() => {
        setGroups((prev) =>
          prev.map((g) => (g.id === id ? { ...g, name: editingName } : g)),
        );
        setEditingId(null);
        setEditingName("");
        onGroupsChanged();
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Aktualisieren der Gruppe");
      });
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingName("");
  };

  const handleDelete = (group: BreadGroup) => {
    const message =
      group.breadNames.length > 0
        ? `Gruppe wirklich löschen? ${group.breadNames.join(", ")} werden dann wieder einzeln berechnet.`
        : "Gruppe wirklich löschen?";
    if (!confirm(message)) return;

    bakeryApi
      .bakeryBreadGroupsDestroy({ id: group.id! })
      .then(() => {
        setGroups((prev) => prev.filter((g) => g.id !== group.id));
        onGroupsChanged();
      })
      .catch((error) => {
        handleRequestError(error, "Fehler beim Löschen der Gruppe");
      });
  };

  return (
    <div className="card shadow-sm">
      <div className="card-header border-0 header-darkbrown-on-sahara">
        <h5 className="mb-0">Gruppen</h5>
      </div>

      <div className="card-body card-body-bakery">
        <p className="text-muted small mb-3">
          Brote einer Gruppe (z.B. aus einem Teig) teilen sich am Backtag Min.
          und Max. Stücke und können zusammen auf einer Etage gebacken werden.
          Zuordnen im Pop-Up „Brot bearbeiten“.
        </p>

        <form onSubmit={handleCreate} className="mb-3">
          <div className="input-group">
            <input
              type="text"
              className="form-control"
              placeholder="Neue Gruppe..."
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
            />
            <button
              type="submit"
              className="btn dark-brown-button"
              disabled={!newGroupName.trim()}
            >
              <Plus size={16} />
            </button>
          </div>
        </form>

        {loading ? (
          <div className="text-center py-4">
            <div className="spinner-border spinner-bakery" role="status">
              <span className="visually-hidden">Lädt...</span>
            </div>
          </div>
        ) : groups.length === 0 ? (
          <div className="text-center py-3 text-muted">
            <p className="mb-0">Noch keine Gruppen vorhanden.</p>
          </div>
        ) : (
          <div className="list-group list-group-flush">
            {groups.map((group) => (
              <div
                key={group.id}
                className="list-group-item px-0 d-flex justify-content-between align-items-start border-0 list-item-transparent"
              >
                {editingId === group.id ? (
                  <div className="flex-grow-1 d-flex align-items-center gap-2">
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSaveEdit(group.id!);
                        if (e.key === "Escape") handleCancelEdit();
                      }}
                    />
                    <button
                      className="btn btn-sm btn-success"
                      onClick={() => handleSaveEdit(group.id!)}
                      disabled={!editingName.trim()}
                    >
                      <Check size={16} />
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={handleCancelEdit}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex-grow-1">
                      <span className="badge badge-bakery-brown">
                        {group.name}
                      </span>
                      <small className="text-muted d-block mt-1">
                        {group.breadNames.length > 0
                          ? group.breadNames.join(", ")
                          : "noch keine Brote"}
                      </small>
                    </div>
                    <div className="btn-group btn-group-sm">
                      <button
                        className="btn btn-outline-secondary border-0 icon-bakery-muted"
                        title="Bearbeiten"
                        onClick={() => handleStartEdit(group)}
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        className="btn btn-outline-danger border-0"
                        title="Löschen"
                        onClick={() => handleDelete(group)}
                      >
                        <Trash size={16} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card-footer border-0 text-muted card-footer-bakery">
        <small>
          {groups.length} Gruppe{groups.length !== 1 ? "n" : ""}
        </small>
      </div>
    </div>
  );
};
