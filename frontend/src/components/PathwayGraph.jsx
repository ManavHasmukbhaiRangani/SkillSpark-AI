/**
 * SkillSpark AI — Pathway Graph
 * Renders learning pathway as interactive node graph.
 * Uses React Flow for dependency-aware visualisation.
 */

import { useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// ── Custom node component ─────────────────────────────────────────

const SkillNode = ({ data }) => {
  const bgColor =
    data.status === "completed" ? "bg-green-500" :
    data.status === "skipped"   ? "bg-gray-400"  :
    data.is_missing             ? "bg-red-500"   :
    data.priority_score > 0.5   ? "bg-red-400"   :
    data.priority_score > 0.25  ? "bg-amber-400" :
                                  "bg-blue-500"  ;

  return (
    <div
      className={`
        px-4 py-3 rounded-xl shadow-lg border-2 border-white
        min-w-32 text-center cursor-pointer
        hover:scale-105 transition-transform duration-200
        ${bgColor}
      `}
      onClick={() => data.onSelect && data.onSelect(data)}
    >
      {/* Skill name */}
      <p className="text-white font-semibold text-sm leading-tight">
        {data.display_name}
      </p>

      {/* Hours + level */}
      <p className="text-white text-xs opacity-80 mt-1">
        {data.duration_hours}h · {data.level}
      </p>

      {/* Status badge */}
      {data.status === "completed" && (
        <p className="text-white text-xs mt-1">✓ Done</p>
      )}
      {data.status === "skipped" && (
        <p className="text-white text-xs mt-1">↷ Skipped</p>
      )}
      {data.quick_win && data.status === "pending" && (
        <p className="text-white text-xs mt-1">⚡ Quick win</p>
      )}
    </div>
  );
};

const nodeTypes = { skillNode: SkillNode };


// ── Build nodes and edges from modules ────────────────────────────

const buildGraph = (modules, onSelect) => {
  if (!modules.length) return { nodes: [], edges: [] };

  const COLS     = 3;
  const H_GAP    = 220;
  const V_GAP    = 160;

  // Build nodes
  const nodes = modules.map((module, index) => {
    const col = index % COLS;
    const row = Math.floor(index / COLS);

    return {
      id:       module.skill_id,
      type:     "skillNode",
      position: {
        x: col * H_GAP + 60,
        y: row * V_GAP + 60,
      },
      data: {
        ...module,
        status:   module.status || "pending",
        onSelect,
      },
    };
  });

  // Build edges from prerequisites
  const edges = [];
  modules.forEach((module) => {
    (module.prerequisites || []).forEach((prereq) => {
      // Only add edge if prereq is in current pathway
      const prereqExists = modules.some(
        (m) => m.skill_id === prereq
      );
      if (prereqExists) {
        edges.push({
          id:             `${prereq}-${module.skill_id}`,
          source:         prereq,
          target:         module.skill_id,
          type:           "smoothstep",
          animated:       module.status === "pending",
          markerEnd: {
            type:  MarkerType.ArrowClosed,
            color: "#94a3b8",
          },
          style: {
            stroke:      "#94a3b8",
            strokeWidth: 2,
          },
        });
      }
    }
    );
  });

  return { nodes, edges };
};


// ── Main PathwayGraph component ───────────────────────────────────

const PathwayGraph = ({ modules = [], onSelectModule }) => {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(modules, onSelectModule),
    [modules, onSelectModule]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync React Flow internal state whenever modules change (e.g. after
  // skip / complete). useNodesState only uses its argument on first render,
  // so without this the graph stays frozen after the initial paint.
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  if (!modules.length) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border
                      border-gray-100 p-6 flex items-center
                      justify-center h-64">
        <p className="text-gray-400">
          No pathway generated yet
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border
                    border-gray-100 overflow-hidden">

      {/* Header */}
      <div className="p-6 border-b border-gray-100">
        <h3 className="text-lg font-bold text-gray-800">
          Learning Pathway
        </h3>
        <p className="text-gray-400 text-sm mt-0.5">
          Dependency-ordered modules — arrows show prerequisites
        </p>
      </div>

      {/* Legend */}
      <div className="px-6 py-3 border-b border-gray-100
                      flex flex-wrap gap-4 text-xs">
        {[
          { color: "bg-red-500",   label: "Missing skill"    },
          { color: "bg-amber-400", label: "High priority"    },
          { color: "bg-blue-500",  label: "Normal priority"  },
          { color: "bg-green-500", label: "Completed"        },
          { color: "bg-gray-400",  label: "Skipped"          },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <div className={`w-3 h-3 rounded-full ${item.color}`} />
            <span className="text-gray-500">{item.label}</span>
          </div>
        ))}
      </div>

      {/* React Flow canvas */}
      <div style={{ height: "500px" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-right"
        >
          <Background color="#f1f5f9" gap={20} />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              const status = node.data?.status;
              if (status === "completed") return "#22c55e";
              if (status === "skipped")   return "#9ca3af";
              if (node.data?.is_missing)  return "#ef4444";
              return "#3b82f6";
            }}
            style={{
              backgroundColor: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
};

export default PathwayGraph;