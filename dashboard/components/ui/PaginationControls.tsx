'use client';

import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

interface PaginationControlsProps {
  page: number;
  totalPages: number;
  total: number;
  limit: number;
  onPageChange: (newPage: number) => void;
  onLimitChange?: (newLimit: number) => void;
  itemName?: string;
}

export function PaginationControls({
  page,
  totalPages,
  total,
  limit,
  onPageChange,
  onLimitChange,
  itemName = 'items',
}: PaginationControlsProps) {
  const [jumpPage, setJumpPage] = useState('');

  if (totalPages <= 1 && total <= limit) {
    return (
      <div className="flex items-center justify-between pt-3 pb-1 text-xs text-zinc-500 font-medium px-2">
        <span>
          Showing all {total.toLocaleString()} {itemName}
        </span>
        <span className="text-[11px] text-zinc-400">Page 1 of 1</span>
      </div>
    );
  }

  const handleJump = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(jumpPage, 10);
    if (!isNaN(parsed) && parsed >= 1 && parsed <= totalPages) {
      onPageChange(parsed);
      setJumpPage('');
    }
  };

  // Generate page numbers to display with smart ellipsis
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const delta = 2; // Number of pages before and after current page

    const left = Math.max(1, page - delta);
    const right = Math.min(totalPages, page + delta);

    if (left > 1) {
      pages.push(1);
      if (left > 2) pages.push('...');
    }

    for (let i = left; i <= right; i++) {
      pages.push(i);
    }

    if (right < totalPages) {
      if (right < totalPages - 1) pages.push('...');
      pages.push(totalPages);
    }

    return pages;
  };

  const startItem = total === 0 ? 0 : (page - 1) * limit + 1;
  const endItem = Math.min(page * limit, total);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 pb-1 px-2 border-t border-zinc-200/60 text-xs">
      {/* Left: Summary and Limit Selector */}
      <div className="flex items-center gap-3 text-zinc-500 font-medium flex-wrap">
        <span>
          Showing <span className="font-bold text-zinc-800">{startItem.toLocaleString()}</span> to{' '}
          <span className="font-bold text-zinc-800">{endItem.toLocaleString()}</span> of{' '}
          <span className="font-bold text-zinc-800">{total.toLocaleString()}</span> {itemName}
        </span>

        {onLimitChange && (
          <div className="flex items-center gap-1.5 pl-2 sm:border-l border-zinc-200">
            <span className="text-[11px] text-zinc-400 font-semibold uppercase">Per page:</span>
            <div className="flex items-center gap-1">
              {[25, 50, 100].map((sz) => (
                <button
                  key={sz}
                  onClick={() => onLimitChange(sz)}
                  className={`px-2 py-0.5 rounded-lg text-[11px] font-bold transition-all cursor-pointer ${
                    limit === sz
                      ? 'bg-zinc-900 text-white shadow-2xs'
                      : 'liquid-pill text-zinc-600 hover:text-zinc-900 hover:bg-white'
                  }`}
                >
                  {sz}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right: Page Buttons & Jump */}
      <div className="flex items-center gap-1.5 flex-wrap justify-end">
        {/* First Page */}
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(1)}
          title="First Page"
          className="liquid-pill p-1.5 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white text-zinc-700 transition cursor-pointer shadow-2xs"
        >
          <ChevronsLeft className="w-3.5 h-3.5" />
        </button>

        {/* Previous */}
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="liquid-pill px-2.5 py-1 rounded-xl text-xs font-semibold disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white text-zinc-700 transition cursor-pointer shadow-2xs flex items-center gap-1"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Prev</span>
        </button>

        {/* Page Number Pills */}
        <div className="flex items-center gap-1">
          {getPageNumbers().map((p, idx) => {
            if (p === '...') {
              return (
                <span key={`ellipsis-${idx}`} className="px-1 text-zinc-400 font-semibold select-none">
                  •••
                </span>
              );
            }
            const pageNum = p as number;
            const isCurrent = pageNum === page;
            return (
              <button
                key={pageNum}
                onClick={() => onPageChange(pageNum)}
                className={`min-w-[28px] h-7 px-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center ${
                  isCurrent
                    ? 'bg-zinc-950 text-white shadow-xs scale-105'
                    : 'liquid-pill text-zinc-700 hover:text-zinc-950 hover:bg-white shadow-2xs'
                }`}
              >
                {pageNum}
              </button>
            );
          })}
        </div>

        {/* Next */}
        <button
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="liquid-pill px-2.5 py-1 rounded-xl text-xs font-semibold disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white text-zinc-700 transition cursor-pointer shadow-2xs flex items-center gap-1"
        >
          <span className="hidden sm:inline">Next</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>

        {/* Last Page */}
        <button
          disabled={page >= totalPages}
          onClick={() => onPageChange(totalPages)}
          title="Last Page"
          className="liquid-pill p-1.5 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white text-zinc-700 transition cursor-pointer shadow-2xs"
        >
          <ChevronsRight className="w-3.5 h-3.5" />
        </button>

        {/* Direct Jump to Page Input */}
        {totalPages > 3 && (
          <form onSubmit={handleJump} className="flex items-center gap-1 ml-1.5 pl-1.5 border-l border-zinc-200">
            <input
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              value={jumpPage}
              onChange={(e) => setJumpPage(e.target.value)}
              placeholder={`Go (1-${totalPages})`}
              className="w-16 px-2 py-1 text-[11px] rounded-lg bg-white/80 border border-zinc-200 text-zinc-900 focus:outline-none focus:ring-1 focus:ring-zinc-900 placeholder:text-zinc-400 font-mono"
            />
            <button
              type="submit"
              disabled={!jumpPage}
              className="liquid-pill px-2 py-1 rounded-lg text-[10px] font-bold uppercase disabled:opacity-30 hover:bg-white text-zinc-700 cursor-pointer shadow-2xs"
            >
              Go
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
