import { LoaderFunctionArgs } from "react-router-dom";
import axios from "axios";

export async function getEntity(id: string) {
  try {
    const res = await axios.get(`http://localhost:8000/topic`, {
      params: {
        topic_id: id,
      },
    });

    return res.data;
  } catch (error) {
    console.error(error);
  }
}

export async function loader({ params }: LoaderFunctionArgs<{ id: string }>) {
  const entity = await getEntity(decodeURIComponent(params.id || ""));
  return { entity };
}
