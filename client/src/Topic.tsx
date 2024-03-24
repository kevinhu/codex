import { useState } from "react";
import { Toaster } from "sonner";
import MistralClient from "@mistralai/mistralai";
import { useLocalStorage } from "usehooks-ts";
import { Link, useLoaderData } from "react-router-dom";
import { ArrowUUpLeft } from "@phosphor-icons/react";
import { TopicWithFindings } from "./App";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";
import { ForceGraph3D } from "react-force-graph";
import SpriteText from "three-spritetext";

export const Topic = () => {
  const { entity } = useLoaderData() as { entity: TopicWithFindings | null };
  const [apiKey, setApiKey] = useLocalStorage<string>("api_key", "");
  const [response, setResponse] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const findings_map =
    entity?.findings?.map((finding) => ({
      id: finding.id || "",
      name: finding.name,
      color: "red",
      type: "finding",
    })) || [];

  const graphData = {
    nodes: [
      {
        id: entity?.id || "",
        name: entity?.name || "",
        color: "blue",
        type: "topic",
      },
      ...findings_map,
    ],
    links:
      entity?.findings?.map((finding) => ({
        source: entity.id,
        target: finding.id,
      })) || [],
  };

  const testMistralEndpoint = async () => {
    setLoading(true);
    const client = new MistralClient(apiKey);

    try {
      const streamResponse = await client.chatStream({
        model: "mistral-large-latest",
        messages: [
          { role: "user", content: "What is the best French cheese?" },
        ],
      });

      setResponse("");

      for await (const chatResponse of streamResponse) {
        setResponse(
          (response) => response + chatResponse.choices[0].delta.content
        );
      }

      console.log(response);
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
          <button className="bg-blue-500 text-white rounded px-3 py-1">
            Generate
          </button>
          <button
            onClick={testMistralEndpoint}
            disabled={loading}
            className="bg-white text-blue-500 border border-blue-500 rounded px-3 py-1 disabled:opacity-50"
          >
            Test endpoint
          </button>

          <div className="border border-gray-300 rounded px-2 py-1 bg-gray-50 whitespace-pre-wrap text-gray-600">
            {response || "What is the best French cheese?"}
          </div>
        </div>

        <div className="border border-gray-200 rounded w-fit overflow-hidden self-center">
          <ForceGraph3D
            width={512}
            height={512}
            backgroundColor={"#f9f9f9"}
            linkColor={() => "rgba(0,0,0,0.2)"}
            graphData={graphData}
            nodeThreeObject={(node: {
              id: string;
              name: string;
              color: string;
              type: string;
            }) => {
              const sprite = new SpriteText(node.name);
              sprite.color = node.color;
              sprite.textHeight = 8;
              return sprite;
            }}
          />
        </div>

        {entity && (
          <div className="flex flex-col space-y-2">
            <h2 className="text-lg">Findings</h2>
            <div className="flex flex-col space-y-2">
              {entity.findings?.length > 0 ? (
                entity.findings.map((finding) => (
                  <div key={finding.id} className="flex flex-col space-y-1">
                    <h3>{finding.name}</h3>
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
