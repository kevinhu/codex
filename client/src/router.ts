import { LoaderFunctionArgs } from "react-router-dom";

export async function getEntity(id: string) {
  return { id };
}

export async function loader({ params }: LoaderFunctionArgs<{ id: string }>) {
  const entity = await getEntity(params.id || "");
  return { entity };
}
