// Tools for the pi threads of the factory: thin wrappers over `bb tasks`.
import { appendFileSync, readFileSync, realpathSync } from "node:fs";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { StringEnum } from "@earendil-works/pi-ai";
import { Type } from "typebox";

const PROJECT = "FAB";
// an agent runs in a directory of its own, where .pi is a symlink back to the factory: that is where state/ lives
const FACTORY = join(realpathSync(".pi"), "..");
// factory/core/board.py writes the run's first task number here; the board tool hides tasks of earlier runs
const runStart = (): number => JSON.parse(readFileSync(join(FACTORY, "state/run.json"), "utf8")).number;
const MESSAGES = join(FACTORY, "state/messages.jsonl"); // the planner's report goes here; factory/core/board.py ends the run on it
// {role: [tool]}, factory/roles/__init__.py writes it at the start of a run: which of the tools below each role may call
const toolsByRole = (): Record<string, string[]> => JSON.parse(readFileSync(join(FACTORY, "state/roles.json"), "utf8"));

// the thread title is "<prompt> [<task>] <model>": the first word is the role, a lead's second word is its epic
let role = "";
let epic = { key: "", id: "" }; // a lead's floor: its tasks get this parent, its board shows only them

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async () => {
    const id = process.env.BB_THREAD_ID;
    if (!id) return;
    const r = await pi.exec("bb", ["thread", "show", id, "--json"], { timeout: 30000 });
    const words: string[] = JSON.parse(r.stdout).thread?.title?.split(" ") ?? [];
    role = words[0];
    const tools = toolsByRole()[role];
    if (tools) pi.setActiveTools(tools);
    if (role === "lead") epic = { key: words[1], id: (await bb(["show", words[1]])).task.id };
  });

  async function bb(args: string[], signal?: AbortSignal): Promise<any> {
    const r = await pi.exec("bb", ["tasks", ...args, "--json"], { signal, timeout: 30000 });
    if (r.code !== 0) throw new Error(`bb tasks ${args[0]}: ${r.stderr || r.stdout}`);
    return JSON.parse(r.stdout);
  }
  const text = (t: string) => ({ content: [{ type: "text" as const, text: t }], details: {} });

  pi.registerTool({
    name: "create_task",
    label: "Create task",
    description:
      "Put a task on the board. type=code goes to a worker, type=test to a tester, type=epic to a lead who " +
      "plans it as sub-tasks and hands the epic back to you (planner only), type=ask to the secretary, who " +
      "asks Mikhail and brings his answer back as the handoff. " +
      "A task with blocked_by starts only after those tasks are done.",
    parameters: Type.Object({
      type: StringEnum(["code", "test", "epic", "ask"]),
      title: Type.String({ description: "The gist of the task in 4-6 words" }),
      motivation: Type.String({ description: "Why this task exists" }),
      dod: Type.String({ description: "Definition of done: how to check it is complete" }),
      priority: StringEnum(["urgent", "high", "medium", "low"]),
      blocked_by: Type.Optional(Type.Array(Type.String(), { description: "Task keys like FAB-3" })),
    }),
    async execute(_id, p, signal) {
      if (role === "lead" && p.type === "epic") throw new Error("a lead cannot create epics; split into code and test tasks");
      const description =
        `## Motivation\n${p.motivation}\n\n## Definition of done\n${p.dod}\n\n` +
        `blocked-by: ${(p.blocked_by ?? []).join(", ") || "none"}`;
      const args = ["create", "--project", PROJECT, "--title", p.title, "--description", description,
                    "--priority", p.priority, "--label", p.type];
      if (role === "lead") args.push("--parent", epic.key);
      const { task } = await bb(args, signal);
      await bb(["update", task.key, "--status", "todo"], signal); // create lands in backlog
      return text(`${task.key} created`);
    },
  });

  pi.registerTool({
    name: "update_task",
    label: "Update task",
    description:
      "Change a task. status=todo sends it back to a worker (rewrite the description first: what was " +
      "wrong, what to do now), status=canceled drops it. " +
      "description replaces the whole text; keep the `## Motivation`, `## Definition of done` " +
      "and `blocked-by:` parts.",
    parameters: Type.Object({
      key: Type.String(),
      status: Type.Optional(StringEnum(["todo", "canceled"])),
      priority: Type.Optional(StringEnum(["urgent", "high", "medium", "low"])),
      description: Type.Optional(Type.String()),
    }),
    async execute(_id, p, signal) {
      const args = ["update", p.key];
      if (p.status) args.push("--status", p.status);
      if (p.priority) args.push("--priority", p.priority);
      if (p.description) args.push("--description", p.description);
      await bb(args, signal);
      return text(`${p.key} updated`);
    },
  });

  pi.registerTool({
    name: "board",
    label: "Board",
    description: "Your tasks with status, priority, type and blockers.",
    parameters: Type.Object({}),
    async execute(_id, _p, signal) {
      const { tasks } = await bb(["list", "--project", PROJECT], signal);
      const start = runStart();
      const mine = (t: any) => role === "lead" ? t.parentTaskId === epic.id : t.parentTaskId === null;
      const lines = tasks.filter((t: any) => t.number >= start && mine(t)).map((t: any) => {
        const blocked = /blocked-by: (.+)/.exec(t.description ?? "")?.[1] ?? "none";
        return `${t.key}  ${t.status}  ${t.priority}  ${t.labels.join(",")}  ${t.title}  [blocked-by: ${blocked}]`;
      });
      return text(lines.join("\n") || "board is empty");
    },
  });

  pi.registerTool({
    name: "show_task",
    label: "Show task",
    description: "Full description and comments (handoffs) of one task.",
    parameters: Type.Object({ key: Type.String() }),
    async execute(_id, p, signal) {
      const { task, comments } = await bb(["show", p.key], signal);
      const log = comments.map((c: any) => `--- ${c.authorName} at ${c.createdAt}\n${c.body}`).join("\n");
      return text(`${task.key} ${task.status} ${task.priority}: ${task.title}\n\n${task.description}\n\n${log}`);
    },
  });

  pi.registerTool({
    name: "handoff",
    label: "Handoff",
    description:
      "Finish your task: what was done (or why it failed), what you noticed, what is left. " +
      "It closes the task; one handoff per task; nothing else reaches whoever created it.",
    parameters: Type.Object({
      key: Type.String({ description: "Your task key" }),
      outcome: StringEnum(["ok", "warning", "failed"], {
        description: "ok = the definition of done is met; warning = met with a caveat; failed = not met (bugs found, work not finished)",
      }),
      summary: Type.String({ description: "The result in 4-6 words" }),
      text: Type.String({ description: "The full handoff" }),
    }),
    async execute(_id, p, signal) {
      await bb(["comment", p.key, "--body", `handoff (${p.outcome}): ${p.summary}\n\n${p.text}`], signal);
      await bb(["update", p.key, "--status", "done"], signal);
      return text(`${p.key} handed off`);
    },
  });

  const message = (fields: Record<string, unknown>) =>
    appendFileSync(MESSAGES, JSON.stringify({ at: new Date().toISOString(), status: null, ...fields }) + "\n");

  pi.registerTool({
    name: "contact_human",
    label: "Contact Mikhail",
    description:
      "Write to Mikhail. You are the only agent who can: nobody else reaches him. " +
      "wait_minutes above zero means you expect an answer — it wakes you when he writes back, or tells you " +
      "he stayed silent when the time is up. wait_minutes 0 just tells him something and waits for nothing.",
    parameters: Type.Object({
      text: Type.String({ description: "The message as he will read it, in his language" }),
      wait_minutes: Type.Number({ description: "How long his answer is worth waiting for; 0 = no answer expected" }),
    }),
    async execute(_id, p) {
      message({ from: "secretary", to: "human", text: p.text, wait_minutes: p.wait_minutes });
      // the time is the secretary's way of telling his answer from what he had written before the question
      const at = new Date().toLocaleTimeString("en-GB");
      return text(p.wait_minutes ? `sent at ${at}; his answer or his silence will wake you` : `sent at ${at}`);
    },
  });

  pi.registerTool({
    name: "tell_planner",
    label: "Tell the planner",
    description:
      "Pass something to the planner: what Mikhail said on his own, outside any task you were given. " +
      "It wakes with your message. Not for the answer to an `ask` task — that is what your handoff is.",
    parameters: Type.Object({ text: Type.String() }),
    async execute(_id, p) {
      message({ from: "secretary", to: "planner", text: p.text });
      return text("the planner will wake with it");
    },
  });

  pi.registerTool({
    name: "report",
    label: "Report",
    description:
      "Planner only. Report on the goal when it is reached or cannot be: what was built, where, what is open. " +
      "The secretary retells it to Mikhail and the run ends.",
    parameters: Type.Object({
      status: StringEnum(["green", "yellow", "red"], { description: "green = goal reached; yellow = with caveats; red = not reached" }),
      summary: Type.String({ description: "The result in 4-6 words" }),
      text: Type.String({ description: "The full report" }),
    }),
    async execute(_id, p) {
      message({ from: "planner", to: "secretary", text: p.summary, details: p.text, status: p.status });
      return text("reported; the secretary passes it on to Mikhail and the run ends");
    },
  });
}
