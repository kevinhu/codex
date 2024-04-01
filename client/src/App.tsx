import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { ForceGraph3D } from "react-force-graph";
import { API_BASE_URL } from "./config";
import logo from "./logo.jpeg";

export interface Topic {
  id: string;
  name: string;
  slug: string;
  type: string;
  description: string;
  is_primary: boolean;
  created_at: string;
}

export interface TopicFinding {
  topic_id: string;
  finding_id: string;
  resolved_topic_id: string;
}

export interface TopicWithFindings extends Topic {
  findings: Finding[];
  data: {
    topics: Topic[];
    findings: Finding[];
    edges: TopicFinding[];
  };
}

export interface Finding {
  id: string;
  name: string;
  slug: string;
  description: string;
  authors: string;
  paper_id: string;
  title: string;
  abstract: string;
  update_date: string;
  created_at: string;
}

const TOGGLES = {
  architecture: true,
  task: true,
  method: true,
  dataset: true,
  benchmark: true,
};

type RawGraph = {
  findings: {
    finding_id: string;
    name: string;
    paper_id: string;
  }[];
  topics: {
    id: string;
    name: string;
    degree: number;
  }[];
  links: {
    topic_id: string;
    finding_id: string;
    resolved_topic_id: string;
  }[];
};

function App() {
  const [query, setQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<Topic[]>([]);
  const [toggles, setToggles] = useState<{ [key: string]: boolean }>(TOGGLES);
  const navigate = useNavigate();

  const [graph, setGraph] = useState<RawGraph>();

  const mappedGraph = useMemo(() => {
    if (!graph) return undefined;
    const topics = graph.topics.map((topic) => ({
      id: topic.id,
      name: topic.name,
      type: "topic",
      color: "blue",
    }));
    const findings = graph.findings.map((finding) => ({
      id: finding.finding_id,
      name: finding.name,
      type: "finding",
      color: "red",
    }));
    return {
      nodes: [...topics, ...findings],
      links: graph.links.map((link) => ({
        source: link.resolved_topic_id,
        target: link.finding_id,
      })),
    };
  }, [graph]);

  useEffect(() => {
    axios.get(`${API_BASE_URL}/graph`).then((response) => {
      setGraph(response.data);
    });
  }, []);

  useEffect(() => {
    if (query.length === 0) {
      setSearchResults([]);
      return;
    }
    try {
      axios
        .get(`${API_BASE_URL}/search`, {
          params: {
            query,
            type_list_str: Object.keys(toggles)
              .filter((key) => toggles[key])
              .join(","),
          },
        })
        .then((response) => {
          setSearchResults(response.data);
        });
    } catch (error) {
      console.error(error);
    }
  }, [query, toggles]);

  const handleClick = useCallback(
    (node: { id: string | undefined; type: string }) => {
      if (node.id) navigate(`/${encodeURIComponent(node.id)}`);
    },
    [navigate]
  );

  return (
    <div className="flex flex-col items-center px-2">
      <div className="flex flex-col w-full max-w-screen-md space-y-6 py-12">
        <div className="flex items-center mt-16 gap-4">
          <img
            src={logo}
            alt="Codex"
            className="w-24 h-24 border-2 shadow-lg rounded-xl"
          />
          <h1 className="text-6xl font-semibold">Codex</h1>
        </div>
        <div className="text-xl">
          <h2>
            <span className="font-bold text-blue-500">53,339</span> papers
            indexed
          </h2>
          <h2>
            <span className="font-bold text-indigo-500">130,427</span> topics
            resolved
          </h2>
          <h2>
            <span className="font-bold text-violet-500">165,131</span> findings
            extracted
          </h2>
        </div>
        {/* Search */}
        <div className="flex flex-col space-y-2">
          <div className="flex space-x-2 justify-end">
            {Object.keys(toggles).map((key) => (
              <div key={key} className="flex items-center space-x-1">
                <input
                  id={key}
                  type="checkbox"
                  checked={toggles[key]}
                  onChange={() =>
                    setToggles({ ...toggles, [key]: !toggles[key] })
                  }
                />
                <label htmlFor={key}>{key}</label>
              </div>
            ))}
          </div>
          <input
            id="search"
            type="text"
            value={query}
            placeholder="Search..."
            onChange={(e) => setQuery(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 w-full"
          />
          <div className="border border-gray-300 rounded px-3 py-2 bg-gray-50 flex flex-col space-y-2">
            {searchResults.map((result) => (
              <Link key={result.id} to={`/${encodeURIComponent(result.id)}`}>
                <div className="flex flex-col space-y-1">
                  <h3>{result.type}</h3>
                  <h2 className="text-lg">{result.name}</h2>
                  <p>{result.description}</p>
                  <hr />
                </div>
              </Link>
            ))}
            {searchResults.length === 0 && "No results"}
          </div>
        </div>
      </div>
      {/* Graph */}
      <div className="px-8 md:px-16 mb-16 w-full h-screen flex flex-col items-center">
        <div className="border border-gray-200 rounded-lg shadow overflow-hidden w-fit">
          <ForceGraph3D
            backgroundColor={"#f9f9f9"}
            linkColor={() => "rgba(0,0,0,0.5)"}
            linkWidth={1}
            graphData={mappedGraph}
            nodeAutoColorBy="color"
            nodeRelSize={8}
            onNodeClick={handleClick}
            nodeLabel={(node) => {
              return `<span class="bg-black rounded-md p-1">${node.name}</span>`;
            }}
            nodeVal={(node) => {
              return node.degree ** 2;
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
