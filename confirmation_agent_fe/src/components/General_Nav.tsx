"use client";

import { log } from "node:console";
import React, { useState, useEffect } from "react";

const General_Nav = () => {
  const [time, setTime] = useState("");
  const [date, setDate] = useState("");

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      const options: Intl.DateTimeFormatOptions = { timeZone: "Europe/Madrid" };
      const madridTime = now.toLocaleTimeString("es-ES", {
        ...options,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });

      const madridDate = now.toLocaleDateString("es-ES", {
        ...options,
        day: "2-digit",
        month: "short",
        year: "numeric",
      });

      setTime(madridTime);
      setDate(madridDate);
      console.log("Reloj actualizado:", madridTime, madridDate);
    };

    updateClock();
    const interval = setInterval(updateClock, 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <nav className="flex items-center justify-between px-6 py-3 bg-nav-primary border-b border-default shadow-sm">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
        <p className="text-white font-bold tracking-wide">Administrador de Llamadas</p>
      </div>
      <div className="flex items-center overflow-hidden rounded-lg" >
        <div className="flex items-center bg-blue-800 border border-white/10 px-4 py-1.5">
          <svg
            className="w-10 h-5 text-brand mr-2"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            fill="white"
            viewBox="0 0 24 24"
          >
            <path
              fillRule="evenodd"
              d="M6 5a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H6Zm0 2h12v11H6V7Zm2 2h2v2H8V9Zm4 0h2v2h-2V9Zm-4 4h2v2H8v-2Zm4 0h2v2h-2v-2Z"
              clipRule="evenodd"
            />
          </svg>
          <span className="text-white font-medium text-xs uppercase tracking-wider tabular-nums">
            {date}
          </span>
        </div>

        <div className="flex items-center bg-neutral-secondary-soft border h-8 border-default-medium px-4 py-1.5">
          <span className="text-xs font-medium text-body uppercase mr-2 tracking-tighter opacity-70">
            Madrid:
          </span>
          <span className="text-gray-600 font-mono text-sm font-semibold tabular-nums">
            {time || "00:00:00"}
          </span>
        </div>
      </div>
    </nav>
  );
};

export default General_Nav;
