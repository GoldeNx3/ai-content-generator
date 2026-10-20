import { Suspense } from "react";

import { AuthForm } from "@/components/auth-form";

export default function LoginPage() {
  // useSearchParams w komponencie klienta wymaga granicy Suspense przy prerenderingu.
  return <Suspense><AuthForm mode="login" /></Suspense>;
}
