<?php
/**
 * Plugin Name: Voyager Shop Fixes
 * Description: Small, reversible usability and SEO fixes for the Voyager Balloons WooCommerce store.
 * Version: 1.3.2
 * Author: Voyager Balloons
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Keep the gallery and lightbox, but avoid WooCommerce's hidden full-resolution
 * hover image. It is not useful on touch devices and adds a large early request.
 */
function voyager_shop_disable_product_gallery_zoom() {
	remove_theme_support( 'wc-product-gallery-zoom' );
}
add_action( 'after_setup_theme', 'voyager_shop_disable_product_gallery_zoom', 100 );

/**
 * Product pages do not contain these optional block, podcast, search or media
 * components. Keep the WooCommerce, Astra and gallery styles untouched.
 */
function voyager_shop_dequeue_unused_product_styles() {
	if ( ! function_exists( 'is_product' ) || ! is_product() ) {
		return;
	}

	$unused_styles = array(
		'wp-block-library',
		'jetpack-block-podcast-episode',
		'wp-block-code',
		'jetpack-search-results-list-style',
		'mediaelement',
		'wp-mediaelement',
		'wc-blocks-style',
	);

	foreach ( $unused_styles as $style_handle ) {
		wp_dequeue_style( $style_handle );
	}
}
add_action( 'wp_enqueue_scripts', 'voyager_shop_dequeue_unused_product_styles', 999 );

/**
 * Return the explicit storefront language without changing WordPress globally.
 */
function voyager_shop_requested_language() {
	if ( isset( $_GET['vb_lang'] ) ) {
		return sanitize_key( wp_unslash( $_GET['vb_lang'] ) );
	}

	if ( isset( $_COOKIE['vb_shop_lang'] ) ) {
		return sanitize_key( wp_unslash( $_COOKIE['vb_shop_lang'] ) );
	}

	return '';
}

/**
 * Complete the missing Spanish product copy for the Braganca experience.
 */
function voyager_shop_translate_braganca_name( $name, $product ) {
	if ( 'es' === voyager_shop_requested_language() && $product && 4174 === (int) $product->get_id() ) {
		return 'Vuelo en globo en Braganza, Portugal';
	}

	return $name;
}
add_filter( 'woocommerce_product_get_name', 'voyager_shop_translate_braganca_name', 20, 2 );

function voyager_shop_translate_braganca_title( $title, $post_id ) {
	if ( ! is_admin() && 'es' === voyager_shop_requested_language() && 4174 === (int) $post_id ) {
		return 'Vuelo en globo en Braganza, Portugal';
	}

	return $title;
}
add_filter( 'the_title', 'voyager_shop_translate_braganca_title', 20, 2 );

function voyager_shop_translate_braganca_short_description( $description, $product ) {
	if ( 'es' !== voyager_shop_requested_language() || ! $product || 4174 !== (int) $product->get_id() ) {
		return $description;
	}

	return voyager_shop_braganca_spanish_short_description();
}
add_filter( 'woocommerce_product_get_short_description', 'voyager_shop_translate_braganca_short_description', 20, 2 );

function voyager_shop_braganca_spanish_short_description() {
	return '<p>Vuelo en globo al amanecer en Braganza, Portugal, por 195&nbsp;&euro; por persona. Incluye brindis con cava, diploma y fotos de la tripulaci&oacute;n cuando est&eacute;n disponibles.</p>';
}

function voyager_shop_translate_braganca_description( $description, $product ) {
	if ( 'es' !== voyager_shop_requested_language() || ! $product || 4174 !== (int) $product->get_id() ) {
		return $description;
	}

	return voyager_shop_braganca_spanish_description();
}
add_filter( 'woocommerce_product_get_description', 'voyager_shop_translate_braganca_description', 20, 2 );

function voyager_shop_braganca_spanish_description() {
	return '<h2>Vuelo en globo al amanecer en Braganza</h2>'
		. '<p>Descubre el entorno de Braganza desde el aire en una experiencia operada por Ao Sabor do Vento y reservada de forma segura a trav&eacute;s de Voyager Balloons EU.</p>'
		. '<ul>'
		. '<li>Vuelo en globo al amanecer en el entorno de Braganza.</li>'
		. '<li>Brindis con cava despu&eacute;s del aterrizaje.</li>'
		. '<li>Diploma de vuelo.</li>'
		. '<li>Fotos de la tripulaci&oacute;n cuando est&eacute;n disponibles.</li>'
		. '<li>Punto exacto confirmado seg&uacute;n la meteorolog&iacute;a y el viento.</li>'
		. '</ul>'
		. '<p><strong>Precio online: 195&nbsp;&euro; por persona.</strong> El pago seguro se procesa en la web de Voyager Balloons EU.</p>';
}

function voyager_shop_translate_braganca_rendered_short_description( $description ) {
	if ( ! is_admin() && 'es' === voyager_shop_requested_language() && 4174 === (int) get_the_ID() ) {
		return voyager_shop_braganca_spanish_short_description();
	}

	return $description;
}
add_filter( 'woocommerce_short_description', 'voyager_shop_translate_braganca_rendered_short_description', 999 );

function voyager_shop_translate_braganca_rendered_description( $description ) {
	if ( ! is_admin() && function_exists( 'is_product' ) && is_product() && 'es' === voyager_shop_requested_language() && 4174 === (int) get_the_ID() ) {
		return voyager_shop_braganca_spanish_description();
	}

	return $description;
}
add_filter( 'the_content', 'voyager_shop_translate_braganca_rendered_description', 999 );

function voyager_shop_translate_braganca_add_to_cart( $text, $product = null ) {
	if ( 'es' !== voyager_shop_requested_language() ) {
		return $text;
	}

	if ( ! $product && function_exists( 'wc_get_product' ) ) {
		$product = wc_get_product( get_the_ID() );
	}

	if ( $product && 4174 === (int) $product->get_id() ) {
		return 'Añadir al carrito';
	}

	return $text;
}
add_filter( 'woocommerce_product_single_add_to_cart_text', 'voyager_shop_translate_braganca_add_to_cart', 20, 2 );
add_filter( 'woocommerce_product_add_to_cart_text', 'voyager_shop_translate_braganca_add_to_cart', 20, 2 );

/**
 * Make Astra quantity controls crawlable and accessible without changing their
 * existing WooCommerce behaviour.
 */
function voyager_shop_fix_quantity_controls() {
	if ( ! function_exists( 'is_product' ) || ! is_product() ) {
		return;
	}
	?>
	<script data-nowprocket id="voyager-shop-quantity-controls">
	(function () {
		'use strict';

		var selector = '.woocommerce .quantity a.ast-qty-placeholder, .woocommerce .quantity a.plus, .woocommerce .quantity a.minus';
		var language = (document.documentElement.lang || 'es').toLowerCase();
		var labels = language.indexOf('en') === 0
			? { plus: 'Increase quantity', minus: 'Decrease quantity' }
			: language.indexOf('pt') === 0
				? { plus: 'Aumentar quantidade', minus: 'Diminuir quantidade' }
				: { plus: 'Aumentar cantidad', minus: 'Reducir cantidad' };

		function fixLink(link) {
			if (!link || !link.classList) {
				return;
			}

			link.setAttribute('href', '#primary');
			link.setAttribute('role', 'button');
			link.setAttribute(
				'aria-label',
				link.classList.contains('plus') ? labels.plus : labels.minus
			);
		}

		function fixRoot(root) {
			if (!root || root.nodeType !== 1) {
				return;
			}

			if (root.matches && root.matches(selector)) {
				fixLink(root);
			}

			if (root.querySelectorAll) {
				root.querySelectorAll(selector).forEach(fixLink);
			}
		}

		function run() {
			fixRoot(document.documentElement);
		}

		document.addEventListener('click', function (event) {
			var link = event.target && event.target.closest
				? event.target.closest(selector)
				: null;

			if (link) {
				event.preventDefault();
			}
		}, true);

		if (document.readyState === 'loading') {
			document.addEventListener('DOMContentLoaded', run, { once: true });
		} else {
			run();
		}

		window.addEventListener('load', function () {
			run();
			window.setTimeout(run, 100);
		}, { once: true });

		new MutationObserver(function (mutations) {
			mutations.forEach(function (mutation) {
				mutation.addedNodes.forEach(fixRoot);
			});
		}).observe(document.documentElement, { childList: true, subtree: true });
	})();
	</script>
	<?php
}
add_action( 'wp_footer', 'voyager_shop_fix_quantity_controls', 100 );
