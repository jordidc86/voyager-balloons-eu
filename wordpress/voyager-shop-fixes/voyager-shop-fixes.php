<?php
/**
 * Plugin Name: Voyager Shop Fixes
 * Description: Small, reversible usability and SEO fixes for the Voyager Balloons WooCommerce store.
 * Version: 1.2.0
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
