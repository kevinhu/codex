import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { ForceGraph3D } from "react-force-graph";
import SpriteText from "three-spritetext";

export interface Topic {
  id: string;
  name: string;
  slug: string;
  type: string;
  description: string;
  is_primary: boolean;
  created_at: string;
}

export interface TopicWithFindings extends Topic {
  findings: Finding[];
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

const N = 300;
const myData = {
  nodes: [...Array(N).keys()].map((i) => ({ id: `${i}`, group: i / 12 })),
  links: [...Array(N).keys()]
    .filter((id) => id)
    .map((id) => ({
      source: `${id}`,
      target: `${Math.round(Math.random() * (id - 1))}`,
    })),
};

function App() {
  const [query, setQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<Topic[]>([]);
  const [toggles, setToggles] = useState<{ [key: string]: boolean }>(TOGGLES);
  const navigate = useNavigate();

  useEffect(() => {
    if (query.length === 0) {
      setSearchResults([]);
      return;
    }
    try {
      axios
        .get(`http://localhost:8000/search`, {
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
    (node: { id: string | undefined }) => {
      if (node.id) navigate(`/${encodeURIComponent(node.id)}`);
    },
    [navigate]
  );

  return (
    <div className="flex flex-col items-center px-2">
      <div className="flex flex-col w-full max-w-screen-md space-y-6 py-12">
        <h1 className="text-3xl mt-16">
          Codex is a search engine and relationship mapping tool for research
        </h1>
        <div className="text-xl">
          <h2>
            <span className="font-bold font-mono">53339</span> papers indexed
          </h2>
          <h2>
            <span className="font-bold font-mono">X</span> topics covered
          </h2>
          <h2>
            <span className="font-bold font-mono">Y</span> findings
          </h2>
        </div>
        <div className="border border-gray-200 rounded w-fit overflow-hidden self-center">
          <ForceGraph3D
            width={512}
            height={512}
            backgroundColor={"#f9f9f9"}
            linkColor={() => "rgba(0,0,0,0.2)"}
            graphData={myData}
            nodeAutoColorBy="group"
            nodeThreeObject={(node: {
              id: string | undefined;
              color: string;
            }) => {
              const sprite = new SpriteText(node.id);
              sprite.color = node.color;
              sprite.textHeight = 8;
              return sprite;
            }}
            onNodeClick={handleClick}
          />
        </div>
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
    </div>
  );
}

export default App;
