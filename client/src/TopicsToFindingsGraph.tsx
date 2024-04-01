import { useLoaderData, useNavigate } from "react-router-dom";
import { TopicWithFindings } from "./App";
import { ForceGraph2D } from "react-force-graph";
import { useCallback, useEffect, useState } from "react";

const NODE_R = 8;

export const TopicsToFindingsGraph = () => {
  const { entity } = useLoaderData() as { entity: TopicWithFindings | null };
  const navigate = useNavigate();

  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());
  const [hoverNode, setHoverNode] = useState<string | null>(null);

  const [graphData, setGraphData] = useState<{
    nodes: {
      id: string;
      name: string;
      color: string;
      type: string;
      neighbors: { id: string }[];
      links: { source: string; target: string }[];
    }[];
    links: { id: string; source: string; target: string }[];
  } | null>(null);

  useEffect(() => {
    const edges =
      entity?.data?.edges.map((edge) => ({
        id: `${edge.finding_id}-${edge.resolved_topic_id}`,
        source: edge.finding_id,
        target: edge.resolved_topic_id,
      })) || [];

    const nodes = [
      ...(entity?.data?.topics.map((topic) => ({
        id: topic.id,
        name: topic.name,
        color: "blue",
        type: "topic",
        neighbors: [
          ...edges
            .filter((edge) => edge.target === topic.id)
            .map((edge) => ({ id: edge.source })),
          ...edges
            .filter((edge) => edge.source === topic.id)
            .map((edge) => ({ id: edge.target })),
        ],
        links: [
          ...edges.filter((edge) => edge.target === topic.id),
          ...edges.filter((edge) => edge.source === topic.id),
        ],
      })) || []),
      ...(entity?.data?.findings.map((finding) => ({
        id: finding.id,
        name: finding.name,
        color: "red",
        type: "finding",
        neighbors: [
          ...edges
            .filter((edge) => edge.target === finding.id)
            .map((edge) => ({ id: edge.source })),
          ...edges
            .filter((edge) => edge.source === finding.id)
            .map((edge) => ({ id: edge.target })),
        ],
        links: [
          ...edges.filter((edge) => edge.target === finding.id),
          ...edges.filter((edge) => edge.source === finding.id),
        ],
      })) || []),
    ];

    const newGraphData = {
      nodes,
      links: edges,
    };

    setGraphData(newGraphData);
  }, [entity?.data]);

  const handleClick = useCallback(
    (node: { id: string | undefined; type: string }) => {
      if (node.id) navigate(`/${encodeURIComponent(node.id)}`);
    },
    [navigate]
  );

  return (
    <>
      {graphData && (
        <ForceGraph2D
          width={512}
          height={512}
          nodeRelSize={NODE_R}
          backgroundColor={"#f9f9f9"}
          linkColor={() => "rgba(0,0,0,0.2)"}
          onNodeClick={handleClick}
          onNodeHover={(node) => {
            setHighlightNodes(new Set());
            setHighlightLinks(new Set());

            if (node?.id) {
              setHighlightNodes(highlightNodes.add(node.id));
              node.neighbors.forEach((neighbor: { id: string }) =>
                highlightNodes.add(neighbor.id)
              );
              setHighlightNodes(highlightNodes);

              node.links.forEach((link: { id: string }) =>
                highlightLinks.add(link.id)
              );
              setHighlightLinks(highlightLinks);
            }

            setHoverNode(node?.id || null);
          }}
          nodeLabel={(node) => {
            return `<span class="bg-black rounded-md p-1">${node.name}</span>`;
          }}
          graphData={graphData}
          nodeCanvasObjectMode={(node) =>
            highlightNodes.has(node.id || "") ? "before" : undefined
          }
          nodeCanvasObject={(node, ctx) => {
            // add ring just for highlighted nodes
            ctx.beginPath();
            ctx.arc(
              node.x || 0,
              node.y || 0,
              NODE_R * 1.4,
              0,
              2 * Math.PI,
              false
            );
            ctx.fillStyle = node.id === hoverNode ? "red" : "orange";
            ctx.fill();
          }}
          linkWidth={(link) => (highlightLinks.has(link.id) ? 5 : 1)}
          linkDirectionalParticles={4}
          linkDirectionalParticleWidth={(link) =>
            highlightLinks.has(link.id) ? 4 : 0
          }
        />
      )}
    </>
  );
};
