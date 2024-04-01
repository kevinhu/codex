import { useCallback, useEffect, useState } from "react";
import { ForceGraph2D } from "react-force-graph";
import { useLoaderData, useNavigate } from "react-router-dom";
import { Finding, Topic, TopicWithFindings } from "./App";
import { renderToString } from "react-dom/server";

const NODE_R = 8;

interface Link extends Finding {
  source: string;
  target: string;
}
interface Node extends Topic {
  neighbors: { id: string }[];
  links: Link[];
}

const GRAY_200 = "rgb(229 231 235)";
const GRAY_400 = "rgb(156 163 175)";
const EMPHASIZED = GRAY_400;
const DEEMPHASIZED = GRAY_200;

const LinkLabel: React.FC<{ link: Link }> = ({ link }) => {
  return (
    <div className="bg-black rounded-md p-1 flex flex-col space-y-1 w-48">
      <h1>{link.name}</h1>
      <p className="text-sm">{link.description}</p>
    </div>
  );
};

const NodeLabel: React.FC<{
  node: Node;
}> = ({ node }) => {
  return (
    <div className="bg-black rounded-md p-1 flex flex-col space-y-1 w-48">
      <h1>{node.name}</h1>
      <p className="text-sm">{node.description}</p>
    </div>
  );
};

export const TopicsToTopicsGraph = () => {
  const { entity } = useLoaderData() as { entity: TopicWithFindings | null };
  const navigate = useNavigate();

  const [topicsGraphData, setTopicsGraphData] = useState<{
    nodes: Node[];
    links: Link[];
  } | null>(null);

  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    // If a node is a finding, for every two topics it is connected to, add a link between those two topics

    // Start with all findings
    const findings = entity?.data?.findings || [];

    // Then for each finding, get the topics it is connected to
    const connectedTopicIds = findings.map((finding) => {
      const connectedTopics = entity?.data?.edges
        .filter((edge) => edge.finding_id === finding.id)
        .map((edge) => ({
          ...finding,
          resolved_topic_id: edge.resolved_topic_id,
        }));
      return connectedTopics || [];
    });

    // Then for each pair of topics, add a link between them
    const connectedTopicPairs = connectedTopicIds
      .map((connectedTopics) => {
        const pairs = [];
        for (let i = 0; i < connectedTopics.length; i++) {
          for (let j = i + 1; j < connectedTopics.length; j++) {
            pairs.push([connectedTopics[i], connectedTopics[j]]);
          }
        }
        return pairs;
      })
      .flat();

    const links =
      connectedTopicPairs.map(([topic1, topic2]) => ({
        ...topic1,
        id: `${topic1.resolved_topic_id}-${topic2.resolved_topic_id}`,
        source: topic1.resolved_topic_id,
        target: topic2.resolved_topic_id,
      })) || [];

    const newTopicsGraphData = {
      nodes:
        entity?.data?.topics.map((topic) => ({
          ...topic,
          type: "topic",
          neighbors: [
            ...links
              .filter((edge) => edge.target === topic.id)
              .map((edge) => ({ id: edge.source })),
            ...links
              .filter((edge) => edge.source === topic.id)
              .map((edge) => ({ id: edge.target })),
          ],
          links: [
            ...links.filter((edge) => edge.target === topic.id),
            ...links.filter((edge) => edge.source === topic.id),
          ],
        })) || [],
      links,
    };

    setTopicsGraphData(newTopicsGraphData);

    // Then, we filter for all nodes that are topics
  }, [entity?.data]);

  const handleRightClick = useCallback(
    (node: { id: string | undefined; type: string }) => {
      if (node.id) navigate(`/${encodeURIComponent(node.id)}`);
    },
    [navigate]
  );

  const handleClick = useCallback(
    (node: Node) => {
      if (selectedNodes.has(node.id)) {
        selectedNodes.delete(node.id);
        setSelectedNodes(selectedNodes);

        // We need to recompute highlighted nodes and links
        // since they could be highlighted because of other nodes?

        const newHighlightedNodes = new Set<string>();
        const newHighlightedLinks = new Set<string>();
        selectedNodes.forEach((selectedNodeId) => {
          const selectedNode = topicsGraphData?.nodes.find(
            (node) => node.id === selectedNodeId
          );
          selectedNode?.neighbors.forEach((neighbor) => {
            newHighlightedNodes.add(neighbor.id);
          });
          selectedNode?.links.forEach((link) => {
            newHighlightedLinks.add(link.id);
          });
        });

        setHighlightNodes(newHighlightedNodes);
        setHighlightLinks(newHighlightedLinks);
      } else {
        selectedNodes.add(node.id);
        setSelectedNodes(selectedNodes);

        // Highlight neighbors
        node.neighbors.forEach((neighbor) => {
          highlightNodes.add(neighbor.id);
        });
        node.links.forEach((link) => {
          highlightLinks.add(link.id);
        });

        setHighlightNodes(highlightNodes);
        setHighlightLinks(highlightLinks);
      }
    },
    [selectedNodes, highlightNodes, highlightLinks, topicsGraphData?.nodes]
  );

  const nodeCanvasObjectMode = useCallback(
    (node: Node) =>
      selectedNodes.has(node.id || "") || highlightNodes.has(node.id || "")
        ? "before"
        : undefined,
    [selectedNodes, highlightNodes]
  );

  const nodeCanvasObject = useCallback(
    // Ignore the type error here
    // eslint-disable-next-line
    (node: any, ctx: any) => {
      // add ring just for highlighted nodes
      ctx.beginPath();
      ctx.arc(node.x || 0, node.y || 0, NODE_R * 1.4, 0, 2 * Math.PI, false);
      ctx.fillStyle = selectedNodes.has(node.id) ? "red" : "orange";
      ctx.fill();
    },
    [selectedNodes]
  );

  return (
    <>
      {topicsGraphData && (
        <ForceGraph2D
          width={512}
          height={512}
          nodeRelSize={NODE_R}
          backgroundColor={"rgb(255 255 255)"}
          linkColor={() => "rgba(0,0,0,0.2)"}
          onNodeClick={handleClick}
          onNodeRightClick={handleRightClick}
          linkLabel={(link) => renderToString(<LinkLabel link={link} />)}
          nodeLabel={(node) => renderToString(<NodeLabel node={node} />)}
          nodeColor={(node) =>
            selectedNodes.size > 0
              ? selectedNodes.has(node.id) || highlightNodes.has(node.id)
                ? EMPHASIZED
                : DEEMPHASIZED
              : EMPHASIZED
          }
          graphData={topicsGraphData}
          onBackgroundClick={() => {
            setSelectedNodes(new Set());
            setHighlightLinks(new Set());
            setHighlightNodes(new Set());
          }}
          nodeCanvasObjectMode={nodeCanvasObjectMode}
          nodeCanvasObject={nodeCanvasObject}
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
