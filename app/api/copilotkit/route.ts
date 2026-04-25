import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const orchestratorUrl =
    process.env.ORCHESTRATOR_URL || "http://localhost:9000";

  const orchestratorAgent = new HttpAgent({
    url: orchestratorUrl,
  });

  const runtime = new CopilotRuntime({
    agents: {
      medok_chat: orchestratorAgent,
    },
  });

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: new ExperimentalEmptyAdapter(),
    endpoint: "/api/copilotkit",
  });

  return handleRequest(request);
}
