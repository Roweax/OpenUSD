// Copyright (c) 2017-2022 Dr. Colin Hirsch and Daniel Frey
// Please see LICENSE for license or visit https://github.com/taocpp/PEGTL/

#ifndef PXR_PEGTL_INTERNAL_HAS_APPLY_HPP
#define PXR_PEGTL_INTERNAL_HAS_APPLY_HPP

#include <utility>

#include "../config.hpp"

namespace PXR_PEGTL_NAMESPACE::internal
{
   template< typename, typename, template< typename... > class, typename... >
   inline constexpr bool has_apply = false;

   template< typename C, template< typename... > class Action, typename... S >
   inline constexpr bool has_apply< C, decltype( C::template apply< Action >( std::declval< S >()... ) ), Action, S... > = true;

}  // namespace PXR_PEGTL_NAMESPACE::internal

#endif
