import { useCallback, useEffect, useState } from "react";
import { Toaster } from "sonner";
import OpenAI from "openai";
import { useLocalStorage } from "usehooks-ts";
import { Link, useLoaderData, useNavigate } from "react-router-dom";
import { ArrowUUpLeft } from "@phosphor-icons/react";
import { TopicWithFindings } from "./App";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import { ForceGraph2D } from "react-force-graph";
import Markdown from "marked-react";

export const Topic = () => {
  const { entity } = useLoaderData() as { entity: TopicWithFindings | null };
  const navigate = useNavigate();

  const [apiKey, setApiKey] = useLocalStorage<string>("api_key", "");
  const [introResponse, setIntroResponse] = useState("");
  const [applicationsResponse, setApplicationsResponse] = useState("");
  const [timelineResponse, setTimelineResponse] = useState("");
  const [testResponse, setTestResponse] = useState<string>("");
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());
  const [hoverNode, setHoverNode] = useState<string | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
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

  const testOpenAIEndpoint = async () => {
    setLoading(true);
    const openai = new OpenAI({
      apiKey,
      dangerouslyAllowBrowser: true,
    });

    try {
      const stream = await openai.chat.completions.create({
        messages: [
          { role: "system", content: "You are a helpful assistant." },
          { role: "user", content: "What is the best French cheese?" },
        ],
        model: "gpt-3.5-turbo",
        stream: true,
      });

      setTestResponse("");

      for await (const chunk of stream) {
        setTestResponse(
          (response) => response + (chunk.choices[0].delta.content || "")
        );
      }
    } catch (error) {
      console.error(error);
    }

    setLoading(false);
  };

  const generateIntro = async (findingsStr: string) => {
    const openai = new OpenAI({
      apiKey,
      dangerouslyAllowBrowser: true,
    });

    try {
      const content = `Your task is to write a readable markdown intro in the style of a Wikipedia page intro using findings from research papers. Include citations when necessary using markdown links to the paper IDs.
This should be no longer than 5 sentences. Focus on what the topic is and why it is important & major conclusions.

Here are the findings for the topic "${entity?.name}":
"""
${findingsStr}
"""
      // `;

      const streamResponse = await openai.chat.completions.create({
        model: "gpt-3.5-turbo",
        stream: true,
        messages: [{ role: "user", content }],
      });

      setIntroResponse("");

      for await (const chatResponse of streamResponse) {
        setIntroResponse(
          (response) => response + (chatResponse.choices[0].delta.content || "")
        );
      }
    } catch (error) {
      console.error(error);
    }
  };

  const generateApplications = async (findingsStr: string) => {
    const openai = new OpenAI({
      apiKey,
      dangerouslyAllowBrowser: true,
    });

    try {
      const content = `Your task is to write a readable markdown section on "Applications" of the given topic in the style of a Wikipedia page section using findings from research papers. Include citations when necessary using markdown links to the paper IDs.
This should be no longer than 10 sentences. If possible, make separate sections or bullet points for different applications.

Here are the findings for the topic "${entity?.name}":
"""
${findingsStr}
"""
      // `;

      const streamResponse = await openai.chat.completions.create({
        messages: [{ role: "user", content }],
        model: "gpt-3.5-turbo",
        stream: true,
      });

      setApplicationsResponse("");

      for await (const chatResponse of streamResponse) {
        setApplicationsResponse(
          (response) => response + (chatResponse.choices[0].delta.content || "")
        );
      }
    } catch (error) {
      console.error(error);
    }
  };
  const generateTimeline = async (findingsStr: string) => {
    const openai = new OpenAI({
      apiKey,
      dangerouslyAllowBrowser: true,
    });

    try {
      const content = `Your task is to write a readable markdown timeline article in the style of a Wikipedia page using findings from research papers. Include citations when necessary using markdown links to the paper IDs

Here are the findings for the topic "${entity?.name}", given in chronological order:
"""
${findingsStr}
"""
      // `;

      const streamResponse = await openai.chat.completions.create({
        messages: [{ role: "user", content }],
        model: "gpt-3.5-turbo",
        stream: true,
      });

      setTimelineResponse("");

      for await (const chatResponse of streamResponse) {
        setTimelineResponse(
          (response) => response + (chatResponse.choices[0].delta.content || "")
        );
      }
    } catch (error) {
      console.error(error);
    }
  };

  const generateArticle = async () => {
    setLoading(true);
    try {
      const chronologicallyOrderedFindings =
        entity?.findings?.sort(
          (a, b) =>
            new Date(a.update_date).getTime() -
            new Date(b.update_date).getTime()
        ) || [];

      const findingsStr = chronologicallyOrderedFindings
        .map((finding) => JSON.stringify(finding))
        .slice(0, 30)
        .join("\n");

      await Promise.all([
        generateIntro(findingsStr),
        generateApplications(findingsStr),
        generateTimeline(findingsStr),
      ]);
    } catch (error) {
      console.error(error);
    }

    setLoading(false);
  };

  const handleClick = useCallback(
    (node: { id: string | undefined; type: string }) => {
      if (node.id) navigate(`/${encodeURIComponent(node.id)}`);
    },
    [navigate]
  );

  const NODE_R = 8;

  return (
    <div className="flex flex-col items-center px-2">
      <Toaster />
      <div className="flex flex-col w-full max-w-screen-md space-y-6 py-12">
        <Link to="/">
          <ArrowUUpLeft size={24} />
        </Link>
        <div className="h-16">
          {entity ? (
            <>
              <h2>{entity.type}</h2>
              <h1 className="text-3xl">{entity.name}</h1>
            </>
          ) : (
            <Skeleton height={30} width={240} />
          )}
        </div>
        <div>
          {entity ? <p>{entity.description}</p> : <Skeleton count={3} />}
        </div>
        <div className="flex flex-col space-y-2 p-4 rounded-md bg-gray-50 border-gray-200 border">
          <p className="text-xl text-gray-700">
            Generate an article for this topic
          </p>

          <label htmlFor="api_key" className="text-gray-500">
            API Key
          </label>
          <input
            id="api_key"
            type="text"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1"
          />
          <button
            onClick={generateArticle}
            disabled={loading}
            className="bg-blue-500 text-white rounded px-3 py-1 disabled:opacity-50"
          >
            Generate
          </button>
          <button
            onClick={testOpenAIEndpoint}
            disabled={loading}
            className="bg-white text-blue-500 border border-blue-500 rounded px-3 py-1 disabled:opacity-50"
          >
            Test endpoint
          </button>

          <div className="border border-gray-300 rounded px-2 py-1 bg-gray-50 whitespace-pre-wrap text-gray-600">
            {testResponse || "What is the best French cheese?"}
          </div>
        </div>
        <div className="markdown">
          <h1>Introduction</h1>
          {introResponse && <Markdown>{introResponse}</Markdown>}
        </div>
        <div className="markdown">
          <h1>Applications</h1>
          {applicationsResponse && <Markdown>{applicationsResponse}</Markdown>}
        </div>
        <div className="markdown">
          <h1>Timeline</h1>
          {timelineResponse && <Markdown>{timelineResponse}</Markdown>}
        </div>
        {graphData && (
          <div className="border border-gray-200 rounded w-fit overflow-hidden self-center">
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
          </div>
        )}
        {topicsGraphData && (
          <div className="border border-gray-200 rounded w-fit overflow-hidden self-center">
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
          </div>
        )}
        {entity && (
          <div className="flex flex-col space-y-2">
            <h2 className="text-lg">Findings</h2>
            <div className="flex flex-col space-y-2">
              {entity.findings?.length > 0 ? (
                entity.findings.map((finding) => (
                  <div key={finding.id} className="flex flex-col space-y-1">
                    <a
                      href={`https://arxiv.org/abs/${finding.paper_id}`}
                      target="_blank"
                      rel="noreferrer"
                      className="underline text-blue-500 text-sm"
                    >
                      {finding.paper_id}: {finding.title}
                    </a>
                    <h3 className="font-bold">{finding.name}</h3>
                    <p>{finding.description}</p>
                    <hr />
                  </div>
                ))
              ) : (
                <>No findings</>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
