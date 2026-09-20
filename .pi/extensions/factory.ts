// Tools for the pi threads of the factory: they read the run's tasks.json and append intents the board folds.
import { appendFileSync, existsSync, mkdirSync, readdirSync, readFileSync, realpathSync } from "node:fs";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { StringEnum } from "@earendil-works/pi-ai";
import { Type } from "typebox";

// an agent runs in a directory of its own, whose .pi/extensions is a symlink to the factory's: two levels up
// from where that really is, state/ lives. Not .pi itself — that is the agent's own directory, skills and all
const FACTORY = join(realpathSync(".pi/extensions"), "../..");
// the run: state/current is a symlink the board points at the run's directory (factory/state.py)
const RUN = join(FACTORY, "state/current");
const TASKS = join(RUN, "tasks.json"); // the board's view of the tasks; factory/core/tracker.py is its only writer
const INTENTS = join(RUN, "intents.jsonl"); // what the tools ask for; the board folds it every tick
const MESSAGES = join(RUN, "messages.jsonl"); // the post; the planner's report goes here and ends the run
const KEYS = join(RUN, "keys"); // one directory per key handed out: mkdir is the atomic counter
// {role: [tool]}, factory/roles/__init__.py writes it at the start of a run: which of the tools below each role may call
const toolsByRole = (): Record<string, string[]> => JSON.parse(readFileSync(join(FACTORY, "state/roles.json"), "utf8"));

// the thread title is "<prompt> [<task>] <model>": the first word is the role, a lead's second word is its epic
let role = "";
let epic = ""; // a lead's floor: its tasks get this parent, its board shows only them
let thread = "";

export default function (pi: ExtensionAPI) {
  pi.on("session_start", async () => {
    thread = process.env.BB_THREAD_ID ?? "";
    if (!thread) return;
    const r = await pi.exec("bb", ["thread", "show", thread, "--json"], { timeout: 30000 });
    const words: string[] = JSON.parse(r.stdout).thread?.title?.split(" ") ?? [];
    role = words[0];
    const tools = toolsByRole()[role];
    if (tools) pi.setActiveTools(tools);
    if (role === "lead") epic = words[1];
  });

  const tasks = (): Record<string, any> => (existsSync(TASKS) ? JSON.parse(readFileSync(TASKS, "utf8")) : {});
  const intents = (): any[] =>
    readFileSync(INTENTS, "utf8").split("\n").filter(Boolean).flatMap((line) => {
      try { return [JSON.parse(line)]; } catch { return []; } // a line another agent is still writing
    });
  const intend = (intent: string, fields: Record<string, unknown>) =>
    appendFileSync(INTENTS, JSON.stringify({ at: new Date().toISOString(), thread, intent, ...fields }) + "\n");
  const known = (key: string) => existsSync(join(KEYS, key.replace(/^FAB-/, ""))); // handed out in this run
  const allocateKey = (): string => {
    for (let n = readdirSync(KEYS).length + 1; ; n++) {
      try { mkdirSync(join(KEYS, String(n))); return `FAB-${n}`; }
      catch (e: any) { if (e.code !== "EEXIST") throw e; }
    }
  };
  const mine = (t: any) => (t.parent ?? null) === (role === "lead" ? epic : null);
  const line = (t: any) =>
    `${t.key}  ${t.status}  ${t.priority}  ${t.type}  ${t.title}  [blocked-by: ${(t.blocked_by ?? []).join(", ") || "none"}]`;
  const text = (t: string) => ({ content: [{ type: "text" as const, text: t }], details: {} });

  pi.registerTool({
    name: "create_task",
    label: "Create task",
    description:
      "Put a task on the board. type=code goes to a worker, type=test to a tester, type=epic to a lead who " +
      "plans it as sub-tasks and hands the epic back to you (planner only), type=ask to the secretary, who " +
      "asks Mikhail and brings his answer back as the handoff. " +
      "A task with blocked_by starts only after those tasks are done: create tasks in order and use the keys " +
      "you got back. To change a task later, `amend_task`; to drop it, `cancel_task`.",
    parameters: Type.Object({
      type: StringEnum(["code", "test", "epic", "ask"]),
      title: Type.String({ description: "The gist of the task in 4-6 words" }),
      motivation: Type.String({ description: "Why this task exists" }),
      dod: Type.String({ description: "Definition of done: how to check it is complete" }),
      priority: StringEnum(["urgent", "high", "medium", "low"]),
      blocked_by: Type.Optional(Type.Array(Type.String(), { description: "Keys of tasks you created, like FAB-3" })),
    }),
    async execute(_id, p) {
      if (role === "lead" && p.type === "epic") throw new Error("a lead cannot create epics; split into code and test tasks");
      const unknown = (p.blocked_by ?? []).filter((k) => !known(k));
      if (unknown.length) throw new Error(`${unknown.join(", ")}: no such task in this run; create tasks in order and use the keys you got back`);
      const key = allocateKey();
      intend("create", {
        key, type: p.type, title: p.title, priority: p.priority, blocked_by: p.blocked_by ?? [],
        description: `## Motivation\n${p.motivation}\n\n## Definition of done\n${p.dod}`,
        parent: role === "lead" ? epic : null,
      });
      return text(`${key} created; it is on the board within a few seconds`);
    },
  });

  pi.registerTool({
    name: "amend_task",
    label: "Amend task",
    description:
      "Add to a task already on the board: a change of scope, a check to drop, something learned since. " +
      "A task not started yet reads it with its brief; an agent already at work is woken with it and goes on. " +
      "Say what changes, not the whole task again. For a task not needed at all, `cancel_task`.",
    parameters: Type.Object({ key: Type.String(), text: Type.String({ description: "What changes, for the agent doing the task" }) }),
    async execute(_id, p) {
      const t = tasks()[p.key];
      if (!t && !known(p.key)) throw new Error(`${p.key}: no such task in this run`);
      if (t && t.status !== "todo" && t.status !== "in_progress") return text(`${p.key} is ${t.status} already, nothing to amend`);
      intend("amend", { key: p.key, text: p.text });
      return text(`${p.key} amended; whoever does it reads it within a few seconds`);
    },
  });

  pi.registerTool({
    name: "cancel_task",
    label: "Cancel task",
    description:
      "Drop a task that is not needed at all: one already in progress is stopped at once and its work is " +
      "discarded. To change a task, `amend_task` instead.",
    parameters: Type.Object({ key: Type.String(), why: Type.String({ description: "One line, for the log" }) }),
    async execute(_id, p) {
      const t = tasks()[p.key];
      if (!t && !known(p.key)) throw new Error(`${p.key}: no such task in this run`);
      if (t && t.status !== "todo" && t.status !== "in_progress") return text(`${p.key} is ${t.status} already, nothing to cancel`);
      intend("cancel", { key: p.key, why: p.why });
      return text(`${p.key} canceled`);
    },
  });

  pi.registerTool({
    name: "set_priority",
    label: "Set priority",
    description: "Move a waiting task up or down. A task already in progress keeps going whatever its priority.",
    parameters: Type.Object({ key: Type.String(), priority: StringEnum(["urgent", "high", "medium", "low"]) }),
    async execute(_id, p) {
      const t = tasks()[p.key];
      if (!t && !known(p.key)) throw new Error(`${p.key}: no such task in this run`);
      if (t && t.status !== "todo") return text(`${p.key} is ${t.status}: the priority of a task matters only while it waits`);
      intend("priority", { key: p.key, priority: p.priority });
      return text(`${p.key} is ${p.priority}`);
    },
  });

  pi.registerTool({
    name: "board",
    label: "Board",
    description: "Your tasks with status, priority, type and blockers. A task created seconds ago shows as pending.",
    parameters: Type.Object({}),
    async execute() {
      const all = tasks();
      const pending = intents().filter((i) => i.intent === "create" && !all[i.key] && mine(i))
        .map((i) => ({ ...i, status: "todo (pending)" }));
      const lines = [...Object.values(all).filter(mine), ...pending].map(line);
      return text(lines.join("\n") || "board is empty");
    },
  });

  pi.registerTool({
    name: "show_task",
    label: "Show task",
    description: "Full description and the handoff of one task.",
    parameters: Type.Object({ key: Type.String() }),
    async execute(_id, p) {
      const all = tasks();
      const t = all[p.key] ?? intents().find((i) => i.intent === "create" && i.key === p.key);
      if (!t) throw new Error(`${p.key}: no such task in this run`);
      const status = all[p.key] ? t.status : "todo (pending)";
      const log = (t.handoffs ?? []).map((h: any) => `--- handoff (${h.outcome}) at ${h.at}: ${h.summary}\n${h.text}`).join("\n");
      return text(`${t.key} ${status} ${t.priority}: ${t.title}\nblocked-by: ${(t.blocked_by ?? []).join(", ") || "none"}\n\n${t.description}\n\n${log}`);
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
    async execute(_id, p) {
      if (!tasks()[p.key]) throw new Error(`${p.key}: no such task in this run`);
      intend("handoff", { key: p.key, outcome: p.outcome, summary: p.summary, text: p.text });
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
      "he stayed silent when the time is up. wait_minutes 0 just tells him something and waits for nothing. " +
      "files go after the text: a png or jpg shows in his chat as a picture, anything else as a document.",
    parameters: Type.Object({
      text: Type.String({ description: "The message as he will read it, in his language" }),
      wait_minutes: Type.Number({ description: "How long his answer is worth waiting for; 0 = no answer expected" }),
      files: Type.Optional(Type.Array(Type.String(), { description: "Absolute paths of files to send him with the text" })),
    }),
    async execute(_id, p) {
      message({ from: "secretary", to: "human", text: p.text, wait_minutes: p.wait_minutes, files: p.files ?? [] });
      // the time is the secretary's way of telling his answer from what he had written before the question
      const at = new Date().toLocaleTimeString("en-GB");
      return text(p.wait_minutes ? `sent at ${at}; his answer or his silence will wake you` : `sent at ${at}`);
    },
  });

  pi.registerTool({
    name: "tell_planner",
    label: "Tell the planner",
    description:
      "Pass something to the planner: what Mikhail said on his own, outside any task you were given, or a " +
      "question of his about the work that you cannot answer from what you have seen. It wakes with your " +
      "message; its answer wakes you. Not for the answer to an `ask` task — that is what your handoff is.",
    parameters: Type.Object({ text: Type.String() }),
    async execute(_id, p) {
      message({ from: "secretary", to: "planner", text: p.text });
      return text("the planner will wake with it");
    },
  });

  pi.registerTool({
    name: "tell_secretary",
    label: "Tell the secretary",
    description:
      "Planner only. Answer the secretary: Mikhail asked how the work goes, what is done, what is stuck, how " +
      "far the finish is. Short, in terms of what he asked for; the secretary retells it. Not the report.",
    parameters: Type.Object({ text: Type.String() }),
    async execute(_id, p) {
      message({ from: "planner", to: "secretary", text: p.text });
      return text("the secretary will wake with it");
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
