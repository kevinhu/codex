import { useState } from "react";
import { Toaster } from "sonner";
import OpenAI from "openai";
import { useLocalStorage } from "usehooks-ts";
import { Link, useLoaderData } from "react-router-dom";
import { ArrowUUpLeft } from "@phosphor-icons/react";
import { TopicWithFindings } from "./App";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import Markdown from "marked-react";
// import { TopicsToFindingsGraph } from "./TopicsToFindingsGraph";
import { TopicsToTopicsGraph } from "./TopicsToTopicsGraph";

const SLD = "http://localhost:5173";

export const Topic = () => {
  const { entity } = useLoaderData() as { entity: TopicWithFindings | null };

  const [apiKey, setApiKey] = useLocalStorage<string>("api_key", "");
  const [introResponse, setIntroResponse] = useState("");
  const [applicationsResponse, setApplicationsResponse] = useState("");
  const [timelineResponse, setTimelineResponse] = useState("");
  const [testResponse, setTestResponse] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(false);

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

  const generateIntro = async (findingsStr: string, topicsStr: string) => {
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

These findings reference other topics. Here are a list of those topics:
"""
${topicsStr}
"""

Whenever you mention a topic, include a link to the topic's page. These links should be in the format [topic name](${SLD}/:id)
Include citations when necessary using markdown links to the paper IDs. These links should be in the format [paper ID](https://arxiv.org/abs/:paper_id)
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

  const generateApplications = async (
    findingsStr: string,
    topicsStr: string
  ) => {
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

These findings reference other topics. Here are a list of those topics:
"""
${topicsStr}
"""

Whenever you mention a topic, include a link to the topic's page. These links should be in the format [topic name](${SLD}/:id)
Include citations when necessary using markdown links to the paper IDs. These links should be in the format [paper ID](https://arxiv.org/abs/:paper_id)

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
  const generateTimeline = async (findingsStr: string, topicsStr: string) => {
    const openai = new OpenAI({
      apiKey,
      dangerouslyAllowBrowser: true,
    });

    try {
      const content = `Your task is to write a readable markdown timeline article in the style of a Wikipedia page using findings from research papers.

Here are the findings for the topic "${entity?.name}", given in chronological order:
"""
${findingsStr}
"""

These findings reference other topics. Here are a list of those topics:
"""
${topicsStr}
"""

Whenever you mention a topic, include a link to the topic's page. These links should be in the format [topic name](${SLD}/:id)
Include citations when necessary using markdown links to the paper IDs. These links should be in the format [paper ID](https://arxiv.org/abs/:paper_id)
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
        .join("\n");

      const topicsStr =
        entity?.data.topics
          .map((topic) =>
            JSON.stringify({
              ...topic,
              id: encodeURIComponent(topic.id) || "",
            })
          )
          .join("\n") || "";

      await Promise.all([
        generateIntro(findingsStr, topicsStr),
        generateApplications(findingsStr, topicsStr),
        generateTimeline(findingsStr, topicsStr),
      ]);
    } catch (error) {
      console.error(error);
    }

    setLoading(false);
  };

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
        {/* <div className="border border-gray-200 rounded w-fit overflow-hidden self-center">
          <TopicsToFindingsGraph />
        </div> */}
        <div className="border border-gray-200 rounded w-fit overflow-hidden self-center">
          <TopicsToTopicsGraph />
        </div>

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
