import type { OtmDocument } from "../types/document";

type PositionedNode = {
  id: string;
  position: { x: number; y: number };
  width?: number | null;
  height?: number | null;
};

export function boundaryFor(doc: OtmDocument, id: string, assigned?: string | null) {
  return (
    doc.trust_boundaries.find((b) => b.id === assigned) ??
    doc.trust_boundaries.find((b) => b.member_component_ids?.includes(id))
  );
}

/** Saved canvas positions override this initial arrangement. */
export function initialPositions(doc: OtmDocument) {
  const groups = new Map<string | undefined, string[]>();
  const memberships = new Map<string, string>();
  const boundaries = new Set(doc.trust_boundaries.map((b) => b.id));
  for (const boundary of doc.trust_boundaries) {
    for (const id of boundary.member_component_ids ?? [])
      if (!memberships.has(id)) memberships.set(id, boundary.id);
  }
  for (const component of doc.components) {
    const assigned = component.in_trust_boundary;
    const key = assigned && boundaries.has(assigned) ? assigned : memberships.get(component.id);
    const members = groups.get(key) ?? [];
    members.push(component.id);
    groups.set(key, members);
  }
  const positions = new Map<string, { x: number; y: number }>();
  let left = 34;
  for (const members of groups.values()) {
    const columns = Math.min(members.length, 4);
    members.forEach((id, index) =>
      positions.set(id, {
        x: left + (index % columns) * 178,
        y: 64 + Math.floor(index / columns) * 120,
      }),
    );
    left += columns * 178 + 29;
  }
  return positions;
}

export function boundaryBoxes(doc: OtmDocument, nodes: PositionedNode[]) {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const assigned = new Map<string, string[]>();
  for (const c of doc.components) {
    if (!c.in_trust_boundary) continue;
    const ids = assigned.get(c.in_trust_boundary) ?? [];
    ids.push(c.id);
    assigned.set(c.in_trust_boundary, ids);
  }
  return doc.trust_boundaries.flatMap((b) => {
    let left = Infinity,
      top = Infinity,
      right = -Infinity,
      bottom = -Infinity;
    for (const id of [...(assigned.get(b.id) ?? []), ...(b.member_component_ids ?? [])]) {
      const node = byId.get(id);
      if (!node) continue;
      left = Math.min(left, node.position.x - 18);
      top = Math.min(top, node.position.y - 39);
      right = Math.max(right, node.position.x + (node.width ?? 156) + 18);
      bottom = Math.max(bottom, node.position.y + (node.height ?? 56) + 19);
    }
    return Number.isFinite(left)
      ? [{ id: b.id, name: b.name, x: left, y: top, width: right - left, height: bottom - top }]
      : [];
  });
}
