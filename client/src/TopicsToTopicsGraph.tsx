import { useCallback, useEffect, useState } from "react";
import { ForceGraph2D } from "react-force-graph";
import { useLoaderData, useNavigate } from "react-router-dom";
import { TopicWithFindings } from "./App";

const NODE_R = 8;

export const TopicsToTopicsGraph = () => {
  const { entity } = useLoaderData() as { entity: TopicWithFindings | null };
  const navigate = useNavigate();

  const [topicsGraphData, setTopicsGraphData] = useState<{
    nodes: {
      id: string;
      name: string;
      color: string;
      type: string;
      neighbors: { id: string }[];
      links: { source: string; target: string }[];
    }[];
    links: { id: string; name: string; source: string; target: string }[];
  } | null>(null);

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
    const connectedTopicPairs = connectedTopicIds.map((connectedTopics) => {
      const pairs = [];
      for (let i = 0; i < connectedTopics.length; i++) {
        for (let j = i + 1; j < connectedTopics.length; j++) {
          pairs.push([connectedTopics[i], connectedTopics[j]]);
        }
      }
      return pairs;
    });

    const newTopicsGraphData = {
      nodes:
        entity?.data?.topics.map((topic) => ({
          id: topic.id,
          name: topic.name,
          color: "blue",
          type: "topic",
          neighbors: [],
          links: [],
        })) || [],
      links:
        connectedTopicPairs.flat().map(([topic1, topic2]) => ({
          id: `${topic1.resolved_topic_id}-${topic2.resolved_topic_id}`,
          name: topic1.name,
          source: topic1.resolved_topic_id,
          target: topic2.resolved_topic_id,
        })) || [],
    };

    setTopicsGraphData(newTopicsGraphData);

    // Then, we filter for all nodes that are topics
  }, [entity?.data]);

  const handleClick = useCallback(
    (node: { id: string | undefined; type: string }) => {
      if (node.id) navigate(`/${encodeURIComponent(node.id)}`);
    },
    [navigate]
  );

  return (
    <>
      {topicsGraphData && (
        <ForceGraph2D
          width={512}
          height={512}
          nodeRelSize={NODE_R}
          backgroundColor={"#f9f9f9"}
          linkColor={() => "rgba(0,0,0,0.2)"}
          onNodeClick={handleClick}
          linkLabel={(link) => {
            return `<span class="bg-black rounded-md p-1">${link.name}</span>`;
          }}
          nodeLabel={(node) => {
            return `<span class="bg-black rounded-md p-1">${node.name}</span>`;
          }}
          graphData={topicsGraphData}
        />
      )}
    </>
  );
};
