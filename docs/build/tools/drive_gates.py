from datetime import date
from resolution.quality_gates import (
    metrics_at_tier_boundaries, bcubed, demote_auto_write_tiers,
    cluster_shape_alerts, pair_key, ClusterShapeContext,
)
from resolution.public_id import PublicIdRegistry

print("== tier-boundary metrics (SIG-IDENT-028) ==")
tiers = {pair_key("a","b"):2, pair_key("c","d"):4, pair_key("e","f"):5}
m = metrics_at_tier_boundaries(tiers, [("a","b"),("c","d")], [("e","f")])
for b, prf in sorted(m.items()):
    print(f"  boundary<= {b}: P={prf.precision:.2f} R={prf.recall:.2f} F1={prf.f1:.2f} (TP={prf.true_positives}/{prf.predicted_positives})")

print("== B-cubed on a seeded bad merge ==")
prf = bcubed({"a":"1","b":"1","c":"1"}, {"a":"x","b":"x","c":"y"})
print(f"  P={prf.precision:.3f} R={prf.recall:.3f} F1={prf.f1:.3f}")

print("== auto-write demotion on a precision breach (SIG-IDENT-028) ==")
for d in demote_auto_write_tiers({0:1.0, 2:0.90, 3:0.995}, threshold=0.97):
    print(f"  tier {d.tier}: precision {d.precision:.3f} -> {d.disposition} (demoted={d.demoted})")

print("== cluster-shape alerts (SIG-IDENT-029) ==")
ctx = ClusterShapeContext(max_le_cluster_size=4, substantial_component_size=3,
                          le_classes=frozenset({"us.le.municipal_police"}))
# oversized LE cluster: 5 PDs linked in a chain, all one cluster
big = {f"pd{i}":"C" for i in range(5)}
edges = [(f"pd{i}", f"pd{i+1}") for i in range(4)]
classes = {f"pd{i}":"us.le.municipal_police" for i in range(5)}
for a in cluster_shape_alerts(big, edges, classes, context=ctx):
    print(f"  {a.kind}: {a.detail}")
# single-bridge join of two triangles
nodes = {n:"K" for n in ["L0","L1","L2","R0","R1","R2"]}
tri = [("L0","L1"),("L1","L2"),("L0","L2"),("R0","R1"),("R1","R2"),("R0","R2"),("L2","R0")]
for a in cluster_shape_alerts(nodes, tri, context=ctx):
    print(f"  {a.kind}: {a.detail}")

print("== public identifier stability across a re-cluster merge (SIG-IDENT-032) ==")
from resolution.er_run import stabilise_cluster_change
reg = PublicIdRegistry(); reg.register("sig:organization:aaa"); reg.register("sig:organization:bbb")
ev = stabilise_cluster_change(reg, before={"e1":"sig:organization:aaa","e2":"sig:organization:bbb"},
                              after={"e1":"joined","e2":"joined"}, dated=date(2026,6,1))
print(f"  event: {ev[0].event_type} sources={ev[0].sources} -> {ev[0].results}")
print(f"  resolve bbb -> {reg.resolve('sig:organization:bbb').status} target={reg.resolve('sig:organization:bbb').target}")
print(f"  resolve aaa -> {reg.resolve('sig:organization:aaa').status} (survivor preserved)")
