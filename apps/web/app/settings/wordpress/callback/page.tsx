import { Suspense } from "react";

import { WordPressCallback } from "@/components/settings/wordpress-callback";

export default function WordPressCallbackPage() {
  // useSearchParams w komponencie klienta wymaga granicy Suspense przy prerenderingu.
  return <Suspense><WordPressCallback /></Suspense>;
}
