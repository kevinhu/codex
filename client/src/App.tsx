import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

export interface Entity {
  id: string;
  name: string;
  slug: string;
  type: string;
  description: string;
  is_primary: boolean;
  created_at: string;
}

function App() {
  const [query, setQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<Entity[]>([]);

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
          },
        })
        .then((response) => {
          setSearchResults(response.data);
        });
    } catch (error) {
      console.error(error);
    }
  }, [query]);

  return (
    <div className="flex flex-col items-center px-2">
      <div className="flex flex-col w-full max-w-screen-md space-y-2 py-12">
        <h1>Codex</h1>
        <input
          id="search"
          type="text"
          value={query}
          placeholder="Search..."
          onChange={(e) => setQuery(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1"
        />
        <div className="border border-gray-300 rounded px-3 py-2 bg-gray-50 flex flex-col space-y-2">
          {searchResults.map((result) => (
            <Link key={result.id} to={`/${encodeURIComponent(result.id)}`}>
              <div className="flex flex-col space-y-1">
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
  );
}

export default App;
